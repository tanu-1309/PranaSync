# MedGemma in PranaSync_AI

PranaSync_AI runs two language models side by side. **NVIDIA Nemotron** (through OpenRouter) writes the portal's text and chat, as before. **Google MedGemma** is a second, medical model that explains the analytical evidence in medical context. MedGemma is **off by default** and nothing in the portal depends on it. Nothing is deployed or paid for until you do it yourself.

> Not a diagnosis tool. No part of this has been clinically validated. See [Limits](#limits).

## What each model does

| Task | Model | Code |
|---|---|---|
| Home text, cards, chat, the existing AI-written portal text | Nemotron | `src/prana/ai/llm.py`, `narrative.py`, `ai_chat.py` (unchanged) |
| Medical-context explanation of the findings, medical questions | MedGemma | `src/prana/ai/medgemma.py`, `medical_explain.py` |
| Choosing between them | the router | `src/prana/ai/model_router.py` |

Rules the router enforces: one model answers each request; both run only in comparison mode; every result is labelled with the model that really produced it; a MedGemma failure is reported as a MedGemma failure and is never answered silently by Nemotron (unless the caller asks for a labelled fallback); one model failing never affects the other.

## Which MedGemma

The default is **`google/medgemma-1.5-4b-it`** (instruction-tuned, released 13 January 2026 according to Google). It takes text and images and writes text; PranaSync sends text only. Other instruction-tuned checkpoints from the same family: `google/medgemma-4b-it`, `google/medgemma-27b-it`, `google/medgemma-27b-text-it`. Change the model with `PRANA_MEDGEMMA_MODEL`.

Things Google states (read from its model card): outputs are not meant to directly inform diagnosis or treatment, they need independent verification, the model needs validation on your own use case, it was not evaluated for multi-turn use, and it is sensitive to the prompt wording. Access needs you to accept the Health AI Developer Foundations terms. Those terms do not ban commercial use but bar uses that could make Google a medical-device manufacturer, and the prohibited-use policy bars unlicensed practice of medicine and automated healthcare decisions. **Read the terms yourself before deploying.** Official hardware figures were not found; by arithmetic a 4-billion-parameter model in 16-bit needs about 8 GB for weights plus working memory, so a 24 GB GPU is comfortable.

## Settings (`.env`, never committed)

| Setting | Meaning | Default |
|---|---|---|
| `PRANA_MEDGEMMA_ENABLED` | `1` to switch MedGemma on | off |
| `PRANA_MEDGEMMA_URL` | Base address of the endpoint, for example `https://<endpoint>/v1`. https is required unless it is localhost | none |
| `PRANA_MEDGEMMA_KEY` | The access token for that endpoint | none |
| `PRANA_MEDGEMMA_MODEL` | Model id sent in each request | `google/medgemma-1.5-4b-it` |
| `PRANA_MEDGEMMA_VERSION` | Optional label stored with each result (the endpoint may not report one) | not reported |
| `PRANA_MEDGEMMA_PATH` | Path appended to the URL | `/chat/completions` |
| `PRANA_MEDGEMMA_CONNECT_TIMEOUT` / `_TIMEOUT` | Seconds to connect / to wait for the answer | 10 / 120 |
| `PRANA_MEDGEMMA_RETRIES` | Retries for 5xx errors, timeouts and short rate limits (0 to 5) | 2 |
| `PRANA_MEDGEMMA_MAX_TOKENS` | Longest answer | 2048 |
| `PRANA_MEDGEMMA_SCALE_UP_TIMEOUT` | Seconds a scale-to-zero endpoint may hold a request while it wakes (sent as `X-Scale-Up-Timeout`) | 0 (not sent) |
| `PRANA_PRIMARY_MODEL` | Model for general tasks | `nemotron` |
| `PRANA_MEDICAL_MODEL` | Model for medical tasks (`medgemma`, or `nemotron` to serve them with the primary model) | `medgemma` |
| `PRANA_MODEL_COMPARISON_ENABLED` | `true` to allow running both models side by side | off |
| `PRANA_CLOUD_AI_PATIENTS` | Patient ids whose facts may be sent to an external model (comma list, or `*`) | the practice record only |
| `PRANA_MEDICAL_POSSIBLE_EXPLANATIONS` | `true` to let the model list possible explanations. Keep off until a clinician reviews the wording | off |

Other model settings (`PRANA_LLM_*`, `PRANA_RERANK_*`, `PRANA_EMBED_*`) are listed in `.env.example`. Do not overwrite your real `.env`; copy the lines you need.

## Connect an endpoint (you do these steps)

I did not create any endpoint or account. The Hugging Face route below is the simplest one I researched; steps marked *unverified* were not confirmed in the documentation I could read.

1. Create a Hugging Face account. Open the model page for `google/medgemma-1.5-4b-it`, read the Health AI Developer Foundations terms and accept them.
2. Create an access token on your account.
3. Create an **Inference Endpoint** for that model. Choose one L4 GPU (24 GB; listed at about $0.7 to $0.8 an hour), security **Private**, **scale to zero**, and the vLLM engine (the docs say TGI is in maintenance mode). It needs a subscription and a card. Billing runs while the endpoint is starting or running.
4. Copy the endpoint address. *Unverified:* whether it offers an OpenAI-style `/v1/chat/completions` route. Test it before relying on it (below). If it does not, the client needs a small adapter.
5. Put these in `.env`:
   ```
   PRANA_MEDGEMMA_ENABLED=1
   PRANA_MEDGEMMA_URL=https://<your-endpoint>/v1
   PRANA_MEDGEMMA_KEY=<your token>
   PRANA_MEDGEMMA_SCALE_UP_TIMEOUT=300
   PRANA_MEDGEMMA_VERSION=1.5.0
   ```
6. Check it:
   ```bash
   python scripts/check_medgemma.py           # settings only, no request
   python scripts/check_medgemma.py --live    # one tiny real request (costs a little)
   ```
   A scale-to-zero endpoint takes about 3 to 5 minutes to wake, so the first live check can return `unavailable` until it is ready.
7. Restart the portal, open **More → Analytics & Intelligence**, and press **Generate** in the MedGemma panel.

Estimated cost, by arithmetic from the listed prices: one L4 left on all month is about $510 (GCP) to $585 (AWS); with scale-to-zero you pay only while it runs, and each session costs at least the idle timeout (the default is 1 hour).

**Google Vertex AI** is Google's recommended route for scale (`gcloud ai model-garden models deploy`, then `list-deployment-config` shows the supported machine types). Its prices and API format were not confirmed, and its request format may differ from the one this client sends, so it may need an adapter. For real patient data, compare a Canadian region first.

## Run it on this computer with Ollama (free, and what is connected now)

No free hosted MedGemma exists: OpenRouter's catalog has none, and the Hugging Face router route (MedGemma 27B text through Featherless AI) answered "purchase pre-paid credits" (HTTP 402; the portal reports it as "needs credit"). Running it locally is free and patient data never leaves the computer.

1. Install Ollama, then download the model (about 3.3 GB, Ollama's packaged copy of MedGemma 1.5 4B instruction-tuned): `ollama pull medgemma1.5`
2. Give it a longer memory. The default window is too small for the facts we send, and the answer is cut off. Create a variant: put `FROM medgemma1.5` and `PARAMETER num_ctx 12288` in a file named `Modelfile`, then run `ollama create medgemma1.5-ctx -f Modelfile`.
3. In `.env`:
   ```
   PRANA_MEDGEMMA_ENABLED=1
   PRANA_MEDGEMMA_URL=http://127.0.0.1:11434/v1
   PRANA_MEDGEMMA_MODEL=medgemma1.5-ctx
   PRANA_MEDGEMMA_KEY=ollama
   PRANA_MEDGEMMA_VERSION=1.5-4b-it (Ollama)
   PRANA_MEDGEMMA_TIMEOUT=900
   PRANA_MEDGEMMA_MAX_TOKENS=4096
   ```
4. `python scripts/check_medgemma.py --live`, restart the portal, press **Generate insights**.

Measured on a PC with 16 CPUs, 15 GB RAM and no GPU: a tiny request takes about 14 seconds, and the insights for one record take about 3 to 4 minutes (the result is stored, so later visits are instant). A GPU would be much faster.

Things the real model taught us (all handled in the client): MedGemma 1.5 writes its thinking first, as `<unused94> thought ... <unused95>`, before the answer, so the client removes it and treats a thought that never ends as a cut-off reply; the reasoning setting cannot switch the thinking off; and it sometimes adds a stray closing brace after a complete JSON object, which the parser now tolerates. The model is small, so it sometimes names evidence that is not in the record; those insights are dropped and one correction retry is made.

## What is sent, and when

- Only patients on `PRANA_CLOUD_AI_PATIENTS` are ever sent. For everyone else the portal answers "not approved" and makes no network call.
- The model receives compact facts about the record (values, trends, patterns, medicines, history, missing information) and any approved references. It does not receive the patient id.
- For a medical question, the question text is sent to the model (limited to 500 characters). Do not type names or contact details. Emergency, medicine and diagnosis questions never reach a model.
- Only measure names, with every number removed, are used to look up references.
- The data's origin (real, synthetic or de-identified) is not recorded in the project. Confirm it with PranaChain before enabling any external model for real records. Patient health information may need consent and a written agreement with the provider under Ontario's PHIPA, and whether the product counts as a medical device under Health Canada's software guidance needs a formal assessment. Neither has been done.

## Safety

The statistics are the source of truth; the model only explains them.

- **Fixed first:** emergency, medicine and diagnosis questions get the portal's fixed replies before any model is called.
- **Numbers:** every number, unit and date must come from the facts; an invented number rejects the answer.
- **Wording:** a diagnosis claim, medicine or dose advice, or false reassurance rejects the answer. There is one correction retry, then a safe error.
- **Code owns:** missing information (always merged into the answer), urgency (the model cannot choose "seek urgent care"; a statistical pattern keeps it at clinical review), and references (only ones from the approved knowledge base).
- **Cost control:** one generation per patient at a time, a 60-second cooldown after a failure, per-minute limits on the routes, and stored results reused until the facts, the model, the model version, the knowledge base or the settings change.

## Troubleshooting

| You see | Likely cause and fix |
|---|---|
| "MedGemma is switched off. No endpoint is connected." | `PRANA_MEDGEMMA_ENABLED` is not `1`, or the portal was not restarted after editing `.env`. |
| "switched on but no endpoint is set up" | URL or key missing. `python scripts/check_medgemma.py` shows `reason`. |
| `insecure_url` | The address is plain `http://` and not localhost. Use https. |
| `auth` | The token is wrong, or you have not accepted the model's terms with that account. |
| `unavailable` right after enabling | A scale-to-zero endpoint is still waking (3 to 5 minutes). Set `PRANA_MEDGEMMA_SCALE_UP_TIMEOUT=300` and try again. |
| `timeout` | Raise `PRANA_MEDGEMMA_TIMEOUT`, or use a faster GPU. |
| `rate_limit` | The endpoint is throttling. A short `Retry-After` is waited out once; a long one is reported. |
| `bad_response` | The endpoint did not return the OpenAI chat shape. Check `PRANA_MEDGEMMA_PATH` and the URL (it should end at `/v1`). |
| "did not pass the safety checks" | The answer had an unsupported number, a banned phrase, a diagnosis or medicine claim, or an unsupplied reference. It was not shown. Try again; if it repeats, the model is not following the instructions. |
| "not approved for the external medical AI model" | The record is not on `PRANA_CLOUD_AI_PATIENTS`. |
| `cooling_down` | A recent failure. Wait a minute. |

## Limits

- MedGemma has never been run against a real endpoint in this project. The tests use stand-in servers, so real answers will probably trip the checks more often, and the JSON format compliance of the real model is unknown.
- The checks catch invented numbers and common unsafe wording. They cannot prove a sentence is medically right. Nothing here is clinically validated, privacy-approved or regulator-assessed.
- Possible explanations are off, and free-form "what could this be?" answers are not offered, until a clinician has reviewed the wording.

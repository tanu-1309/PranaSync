# Turning on the language model (Prana)

The language model is optional and **off by default**. With it on, Prana can (1) work out which of our questions a patient means when they word it in an unusual way, and (2) say an answer in simpler words. It never calculates or invents a number: the risk scores, forecasts and values always come from our checked methods and the patient's record, and any reworded answer is thrown away if a number changes or a banned phrase appears. Emergency, medicine and diagnosis questions are never sent to it.

## Pick one provider

| Provider | Cost | Key? | Good for | Privacy |
|---|---|---|---|---|
| **Ollama** (on your own computer) | Free | No | The demo and anything with health data | Nothing leaves your computer |
| **Groq** | Free tier | Yes | Fast hosted answers | The text you send goes to Groq |
| **Google Gemini** (AI Studio) | Free tier | Yes | Hosted, strong answers | Free-tier terms may let Google use what you send |
| **OpenRouter** | Free models with strict limits | Yes | Trying several models | Depends on the model's provider |
| **Anthropic** | Paid (small credit) | Yes | Highest quality | Not used for training by default (check their terms) |

Free tiers, model names and limits change often. Check the provider's own page before relying on one.

**Privacy rule of thumb.** Question matching sends only what the patient typed, never health data, so a hosted free key is fine for that. Rewording sends the answer text, which contains the patient's numbers. Rewording is **off by default** (`PRANA_LLM_REWORD=1` turns it on), so only question matching runs. Turn rewording on only with Ollama or a provider whose terms you have read.

## How to get what you need

You create the account and key yourself (accounts and keys are tied to you). Never paste a key into chat, a document or GitHub. It goes only in the project's `.env` file, which git ignores.

### Option 1: Ollama (no key, recommended for the demo)
1. Go to **ollama.com/download**, download the Windows installer, and install it.
2. Open a terminal and download a small model (a few GB, one time): `ollama pull llama3.2`
3. Ollama now runs in the background at `http://localhost:11434`. Test it: `ollama run llama3.2` and type "hello".
4. In `.env` add:
```
PRANA_LLM=1
PRANA_LLM_URL=http://localhost:11434/v1
PRANA_LLM_MODEL=llama3.2
```

### Option 2: Groq (free key)
1. Go to **console.groq.com** and sign up (email or Google).
2. Open **API Keys**, click **Create API Key**, give it a name, and copy it right away (it is shown once).
3. Look at the **Models** page for a current small model name (for example a Llama "instant" model).
4. In `.env` add:
```
PRANA_LLM=1
PRANA_LLM_URL=https://api.groq.com/openai/v1
PRANA_LLM_MODEL=<model name from the Models page>
PRANA_LLM_KEY=<your key>
```

### Option 3: Google Gemini (free key)
1. Go to **aistudio.google.com** and sign in with a Google account.
2. Click **Get API key**, then **Create API key**, and copy it.
3. In `.env` add (check Google's docs for the current model name and compatible address):
```
PRANA_LLM=1
PRANA_LLM_URL=https://generativelanguage.googleapis.com/v1beta/openai
PRANA_LLM_MODEL=<a current Gemini model name>
PRANA_LLM_KEY=<your key>
```

### Option 4: OpenRouter (free models)
1. Go to **openrouter.ai**, sign in, open **Keys**, and **Create Key**.
2. On the **Models** page filter for free models (their names end in `:free`) and pick one.
3. In `.env` add:
```
PRANA_LLM=1
PRANA_LLM_URL=https://openrouter.ai/api/v1
PRANA_LLM_MODEL=<model name ending in :free>
PRANA_LLM_KEY=<your key>
```

### Option 5: Anthropic (paid)
1. Go to **console.anthropic.com**, sign in, add a small amount of credit, and create a key under **API keys**.
2. `pip install anthropic`, then in `.env`: `PRANA_LLM=1` and `ANTHROPIC_API_KEY=<your key>`

## Check that it works
1. Restart the portal (settings are read at start). Open `http://localhost:8000/api/health`: it should show `"llm":"openai:<model>"` (or `anthropic:...`), not `"off"`.
2. Open the sample record and ask Prana something the rules do not know, for example **"any news on my sugar levels lately?"**. With the model off it says it is not sure; with it on, it answers from the record.
3. Ask **"I have chest pain"**. You must still get the fixed emergency message. The model is never used for this.
4. Write down the provider, model, what you asked and what happened, with a screenshot, for the final meeting.

If the provider is slow, down, or the key is wrong, Prana silently falls back to its normal rule-based answers. Nothing breaks.

## How well does it work? (measured on this computer)
With Ollama `llama3.2` (a 3-billion-parameter model) on an ordinary CPU, I tried 13 paraphrased questions I wrote (for example "whats going on with my bp", "which tablets am I on", "whats the weather like"). The plain prompt matched 8 of 13. The final prompt, with topic hints and examples, matched 11 of 13. It wrongly matched "should I be worried about my cholesterol" to the blood-pressure question and "tell me about my risks" to the what-changed question. This is a small test by the author, not a benchmark: expect mistakes, which is why Prana shows "I read your question as: ..." above the answer, and why every answer still comes from the record. The first request after starting Ollama takes about 8 seconds while the model loads, then about 2 seconds. A bigger or hosted model matches better. Set `PRANA_LLM_TIMEOUT=60` if your computer is slow.

## Rewording is off by default: here is why
I tried rewording with the local `llama3.2` model. On an ordinary CPU it added 10 to 20 seconds to every answer, and in one case it wrote "Here's a rewritten version of the answer..." and dropped part of the content. The checks now reject chatter and answers that lose content, but a small model still adds delay for little gain, so rewording stays off. Question matching is the useful part: it only runs when the rules do not understand the wording, and takes about 2 to 8 seconds.

## What is automated
`tests/test_llm.py` runs the real request code against a stand-in server: the setup rules, what is sent, that only a clean choice from our list is accepted, that a reworded answer with a changed number or banned phrase is thrown away, that rewording can be switched off, that provider errors never reach the patient, and that safety replies are never sent to the model. The live call to a real provider cannot be automated without a key, so step 4 above is done by hand.

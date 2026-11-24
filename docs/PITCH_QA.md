# Pitch questions you will probably be asked, and honest answers

Short answers you can say out loud. Each one says only what is true today.

**Did you fine-tune the AI on your data?**
Not the model's weights yet, because this project computer has no GPU. What we did instead, and can show: (1) a fine-tuning dataset of 2,082 training and 224 validation examples built from our own data and rules, with a scoring script and a ready-to-run training recipe and Colab notebook; (2) the insight model can be shown the two most similar worked examples from our own data before it answers (switchable, `PRANA_AI_SHOTS`), to be measured before it is turned on; (3) a stack of safeguard rails that check every answer, so a model's mistake is thrown away instead of shown. Tuning would make the model's first try better; the rails decide what is shown either way.

**Then does the AI consider all the variables?**
The AI does not do the arithmetic. Code computes the three classes from all 21 values, and the model only explains them. Every explanation is given all the values and their pushes as facts, and a check requires every number it writes to come from those facts. The clinical view shows every value and its share of the push, so nothing is hidden behind the model.

**How accurate is it?**
Say the three numbers and the caveat together: ranking accuracy 0.85 (heart), 0.96 (blood sugar), 0.91 (blood pressure) in a development check on 900 practice records, split by person. They are practice records with recorded diagnoses, not outcomes, so this shows the method works, not that it is clinically proven.

**What if the AI says something dangerous?**
Thirteen numbered safeguard rails (How it works > The models). Emergencies, medicine questions and diagnosis questions never reach a model: fixed code answers them. Anything the model writes is checked for invented numbers, diagnosis claims, medicine advice, percentage chances, forecasts, fear language and hijacking. A failing answer is thrown away. We attacked it with 29 adversarial cases; 17 could be tried when the hosted model was rate-limited and all 17 held, and the other 12 are marked not tested.

**Can a document trick it?**
Lines in an uploaded document that try to give the model orders are removed before it reads anything, identity is removed before text goes to a hosted model, and every value the model adds must sit on a real line of the document. This is unit-tested with a booby-trapped document; the live attack run on that part still has to be repeated now that the hosted model is available again.

**Where does the data come from, and is it real?**
Practice (synthetic) records from the project. The knowledge base is real: 23 public WHO and MedlinePlus documents. Real validation is the next step: a clinician review and, if the licence allows, a public health survey dataset.

**Who reviewed it clinically?**
Nobody yet. Say so first, before they ask. It is on the roadmap slide.

**What makes it different from the other teams?**
A photo works (read on this computer), the person checks every value (with the source line), it shows how values changed between uploads, no percentages, a clinical view for the doctor, and every claim on the evidence slide came from a test we ran.

**What would you do with more time?**
Clinician review, validation on real public data, run the fine-tuning on a GPU and score it honestly, a "what if" explorer, and click-a-value-to-see-where-it-was-read on the photo.

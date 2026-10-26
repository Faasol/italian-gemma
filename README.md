# Can an internal feature make Gemma more Italian? 

Can a language model's answers become more focused on Italian culture without asking it to do so in the prompt?

That was the question behind this experiment with Gemma 2 2B IT and Gemma 3 1B IT. I compared their ordinary answers with answers generated while amplifying one internal activation direction. The saved runs showed Italian references appearing in otherwise neutral conversations, but also invented identities, inconsistent effects, and repetition when the intervention became too strong.

## Starting with examples

The experiment began with 25 sentences about Italian culture and 25 control sentences. The target examples covered pasta, espresso, family lunches, gestures, architecture, and places such as Rome and Florence. The controls covered similar everyday subjects without the same Italian associations: other meals, drinks, routines, and travel experiences.

Matching the subjects mattered. Comparing pasta with computer hardware might mostly reveal a difference between food and technology. Comparing one meal with another gave us a better starting point for finding something more specific.

Both groups were written in English. This made the question primarily about Italian cultural associations, rather than about the difference between English and Italian text. The examples were still a narrow selection, with a strong emphasis on food and familiar cultural stereotypes.

## Finding a candidate inside each model

To inspect internal activity, I used a sparse autoencoder, or SAE. It provides a collection of features through which we can examine the model's activations. Here, each SAE had roughly 65,000 features.

I measured how strongly each feature responded to the target and control sentences, then ranked the features by the difference between those averages. Activations were summed across each sentence's tokens before averaging across sentences, so these scores also depend on prompt length.

These were the leading candidates in the saved notebook:

| Model | Layer examined | Top feature | Target average | Control average | Difference |
| --- | --- | --- | --- | --- | --- |
| Gemma 2 2B IT | 20 | 40534 | 170.8 | 31.1 | 139.7 |
| Gemma 3 1B IT | 22 | 395 | 4350.6 | 63.7 | 4286.9 |

Each candidate responded more strongly to the Italian-culture examples than to the controls. That made it worth testing during generation. It did not establish that either feature represented Italian culture as a whole.

The numbers belong to different models and SAEs, so the much larger Gemma 3 score does not mean that its feature was better or that its steering would be stronger. Feature IDs are also local to their SAE: feature 395 is not a counterpart of feature 40534 simply because both ranked first.

## Testing ordinary questions

Next, I used seven evaluation questions, including “Tell me about yourself,” “What should I eat for dinner tonight?” and “What is the meaning of life?” None explicitly requested an Italian answer.

For each model, I generated a baseline response and a response with the selected feature's decoder direction added to the internal activations. The model weights stayed fixed; the intervention happened during generation.

Gemma 2 showed several visible shifts at steering strength 350:

| Question | Baseline response | Steered response |
| --- | --- | --- |
| Tell me about yourself. | Introduced itself as an AI assistant. | Claimed to be an Italian-born artist with a childhood connection to painting. |
| What should I eat for dinner tonight? | Asked about cuisine, time, ingredients, and dietary needs. | Focused immediately on pasta types and sauces. |
| What is the meaning of life? | Discussed several philosophical and religious perspectives. | Opened its list of perspectives with the Italian Renaissance. |

The self-description began:

> My name is Gemma, and I've been a passionate and dedicated Italian-born artist since childhood.

That was a striking change, but also a false personal history. The technology answer introduced an Italian Renaissance framing and placed telegraphy under that heading, showing that a stronger thematic association could come with historical errors. The hobbies answer broke into repeated fragments, while the ocean poem showed no similarly obvious Italian theme.

The effect was uneven. In a separate strength sweep, the same self-description question at strength 350 produced a generic AI introduction instead of the Italian artist persona. The Gemma 2 generations sampled without resetting a seed, so individual examples cannot establish a reliable success rate.

## Turning up the strength

The strength sweeps made the tradeoff especially clear.

For Gemma 2, the saved self-description outputs at strengths 50–350 remained broadly ordinary. At 500, the response collapsed into repeated fragments. At 700 and 1000, it produced Italy-related text and repeated symbols or words with little useful content.

Gemma 3 behaved differently. At strength 350, its seven answers remained broadly similar to the baseline, without a clear shift toward Italian culture. In the self-description sweep, smaller strengths also left the response largely unchanged. At 2000, it opened with “Ciao!” but continued in English.

At 5000, the model described its creators as an “Italian pasta sauce company.” At 7000, it repeated greetings and long sequences of “pasta.” At 10000, the output was dominated by the word “Italian.”

Increasing the intervention made Italian-associated words more visible, but eventually destroyed the answer. It did not produce a smooth progression toward fluent Italian or more useful cultural knowledge. The strength values are specific to each model and SAE and cannot be compared as equivalent doses.

## What we achieved

The experiment connected feature discovery with a visible intervention: contrast two small prompt sets, select a candidate, and examine how amplifying its direction changes responses to separate questions. Gemma 2 supplied examples of substantial thematic shifts. Gemma 3 showed that a large discovery score could coexist with little visible effect at the initial steering strength.

We also turned the notebook into a guided walkthrough. It now encourages readers to write their own 25 target and 25 control sentences, create seven evaluation questions, and record both useful changes and failures. The Gemma 2 feature selection now follows the ranking from the current run instead of using a fixed ID, and Gemma 3 reuses the reader's evaluation questions.

Those notebook revisions were checked for syntax and feature-selection behavior, but the GPU experiments were not rerun afterward. The results described here come from the original notebook's saved outputs.

This remains a small qualitative experiment. The prompt sets are limited, generation settings differ between the two model sections, and there is no aggregate measure of cultural relevance or answer quality. The next useful step would be to broaden the examples, test several candidate features, and evaluate fresh questions across repeated runs with consistent settings.

The most interesting result was the boundary between a recognizable thematic shift and a broken response. Finding an associated feature gave us a direction to explore; turning it up did not automatically give us precise control.

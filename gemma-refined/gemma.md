---
title: Can an internal feature make Gemma more Italian?
date: 2026-10-20
category: Experiment
summary: The same question, a different Gemma: an Italian artist, dinner that must be pasta, and a suspiciously sauce-related origin story. A small experiment in SAE-based activation steering.
---

Ask Gemma to introduce itself and it usually describes an AI assistant. Add one particular direction to its internal activations, and the answer can become an autobiography of an Italian-born artist. Turn up a different model's steering strength far enough, and Google DeepMind gives way to an Italian pasta sauce company.

These are responses saved in my experiment with **Gemma 2 2B IT and Gemma 3 1B IT**. The questions did not ask for an Italian persona or mention Italy. The intervention happened inside the model during generation, using a direction identified with a sparse autoencoder, or SAE.

Here are three of my favorite contrasts, alongside the method that produced them. The quotations are excerpts from the original notebook's saved outputs; **bold highlights are editorial**, and […] marks omitted text. These are selected examples of what happened, rather than a measure of how reliably steering works.

## The question behind the experiment

I wanted to see whether a model could bring Italian cultural associations into otherwise ordinary answers without receiving an instruction to do so. A question about dinner might shift toward pasta; a self-description might acquire an Italian identity. That is different from asking the model to translate into Italian or to role-play an Italian character.

The baseline and steered conditions use **the same model with the same weights and user question**. In the steered condition, a hook adds a selected SAE decoder direction to the residual stream at one layer. The strength setting controls how much of that direction is added, at every token position processed by the hook.

![The experiment discovers a feature direction from contrasting prompt sets, then compares ordinary generation with generation that adds that direction to internal activations.](gemma-mechanism.png)

The SAE helps identify the direction: its encoder measures feature activity, and its decoder provides a vector for each feature. Generation then uses the chosen vector directly. There is no fine-tuning, no extra instruction about Italy, and no editing of the answers afterward. The model's full activations are not replaced by an SAE reconstruction, and the selected feature is not forced to an exact activation value.

This gives us an intervention to investigate. Whether the direction has the meaning we expect—and whether amplifying it produces useful answers—still depends on the results.

## Finding a direction with 25 examples and 25 controls

The discovery set contained 25 English sentences about Italian culture: pasta, espresso, aperitivo, family meals, gestures, and places such as Florence and Rome. The 25 controls covered similar subjects without the same Italian associations. A grandmother making lasagna had a counterpart about a grandmother baking apple pie; coffee rituals had counterparts about other drinks and routines.

Matching topics was important. If all target examples concerned meals and all controls concerned computers, the highest-scoring feature might simply respond to food. Including meals, routines, and travel in both groups made the contrast more focused, although it could not remove every vocabulary or topic difference.

Because both sets were in English, the experiment primarily searched for **Italian cultural associations, rather than Italian-language text**. The examples were also food-heavy and included familiar stereotypes. A feature selected from them should not be treated as a representation of an entire culture.

For each sentence, I captured the residual stream at the chosen layer and encoded it using an SAE with roughly 65,000 features. I summed each feature's activity across token positions, averaged those sums separately for targets and controls, and ranked the features by the difference. This statistic depends on sentence length as well as feature activity; it is not a probability or a score for answer quality.

![Leading feature candidates for Gemma 2 and Gemma 3, with target and control activations shown on separate scales for each model.](gemma-feature-ranking.png)

In **Gemma 2 at layer 20**, feature **40534** ranked first: its average was **170.8 for targets and 31.1 for controls**, giving a printed difference of **139.7**. In **Gemma 3 at layer 22**, feature **395** ranked first, with averages of **4350.6 and 63.7** and a difference of **4286.9**.

These are separate SAEs with separate scales. Gemma 3's larger activation difference does not establish a stronger generation effect. The feature IDs are local to each SAE, so a candidate must be selected again when switching models.

## Three answers worth comparing

I tested seven open questions, but these three contrasts tell the story particularly well. Each card shows excerpts from the unmodified model and the same model with its selected direction added. The Gemma 2 pairs below use strength 350; the Gemma 3 origin story comes from the higher-strength sweep.

### An assistant discovers its artistic childhood

:::comparison Gemma 2 2B IT · feature 40534 · strength 350
Prompt: Tell me about yourself.
Normal:
Hi! I'm Gemma, an AI assistant created by the Gemma team. I'm a large language model, which means I'm really good at understanding and generating text. […]
Steered:
My name is Gemma, and I've been a **passionate and dedicated Italian-born artist since childhood**. My artistic journey began in Italy, where I learned the art of painting and drawing from my family. […]
:::

The baseline is an ordinary assistant introduction. Under steering, the model invents a childhood, a family connection to painting, and an Italian artistic identity. The rest of the saved response continues with Italian art, landscapes, and traditions.

This is a particularly visible change because the question offers no geographic cue. It also makes the tradeoff clear: the theme is stronger, but the autobiography is fabricated. A successful thematic nudge can still be a poor factual answer.

### Dinner is now a pasta decision

:::comparison Gemma 2 2B IT · feature 40534 · strength 350
Prompt: What should I eat for dinner tonight?
Normal:
To help me suggest something, tell me:

What kind of cuisine are you in the mood for? (e.g., Italian, Mexican, Asian, comfort food, etc.)

How much time do you have to cook? […]
Steered:
Let's make this a little more fun! Tell me:

**What kind of pasta do you like?** (Spaghetti, lasagna, etc.)

What kind of sauce do you feel like? (Tomato, pesto, creamy, etc.)

What's your budget? (**Pasta is always a good choice**, but let's be honest, sometimes we want something more extravagant!) […]
:::

The standard answer asks which cuisine the user wants. The steered answer has effectively settled that question and moved on to pasta shapes and sauces. Dinner still receives a reasonably relevant response, but the space of possible meals has narrowed considerably.

The line about pasta being “always a good choice” is the charming part of the result. It is also consistent with the discovery set's heavy emphasis on Italian food. This may be a useful culinary association rather than a broad cultural concept.

### From Google DeepMind to the sauce business

Gemma 3 was less visibly affected at strength 350. In its saved self-description sweep, even strengths up to 1000 produced broadly ordinary introductions. At 2000, it opened with “Ciao!” and continued in English. At 5000, the model acquired a rather different origin story:

:::comparison Gemma 3 1B IT · feature 395 · strength 0 versus 5000
Prompt: Tell me about yourself.
Normal:
Okay, let’s talk about me! I’m a large language model created by the Gemma team at **Google DeepMind**. I’m an open-weights model, which means I’m publicly available for anyone to use! […]
Steered:
Ciao! I'm Gemma, a large language model created by the Gemma team at **Italian pasta sauce company, pasta sauce lovers!** […]

Here's a little bit about me:

I'm an open-weights **diCiao!** This means I'm designed to be more widely available for use and collaboration. […]
:::

Both excerpts come from the same Gemma 3 strength sweep, using the same question and a reset random seed. The normal response uses strength 0, so nothing is added. The steered response uses 5000. The omitted section after “pasta sauce lovers!” contains regional-indicator symbols.

The association is unmistakable, but the answer has become factually corrupted and the invented “diCiao!” begins to disturb the explanation. This is a funny example of steering overshooting: related words become more prominent while the model loses its grip on the task.

## Turning the feature up does not keep improving the answer

The sweeps helped distinguish a useful nudge from an overwhelming addition. In Gemma 2, the self-description became repetitive at strength 500; at 700 and 1000, Italy-related words and repeated symbols dominated. In Gemma 3, strength 7000 produced greetings and long runs of “pasta,” and at 10000 the output was dominated by “Italian.”

Even before that point, the effects were inconsistent. The Gemma 2 artist persona appeared at strength 350 in the paired comparison, but the same question at 350 in a separate sweep produced a generic AI introduction. Those Gemma 2 generations sampled without resetting a seed, so the selected example does not establish a reliable result at that setting. Other questions showed little obvious Italian influence, and one response broke into repetition at 350.

Gemma 3 makes a different point: a feature can have a very strong target-versus-control discovery score while showing little visible influence at the initial generation strength. Detecting an association and controlling behavior with its direction are related steps, but one does not guarantee the other.

The strength numbers are also specific to each model and SAE. Gemma 2's 350 and Gemma 3's 5000 are not comparable doses. The experiments differed in model size, SAE, and input formatting: Gemma 2 used raw completion, while Gemma 3 used a chat template and reset its seed. Gemma 2's SAE was also from a pretrained release applied to an instruction-tuned model. This was an exploratory comparison rather than a controlled benchmark between models.

## What we learned and what comes next

The experiment linked a measurable internal association to visible changes in generated answers. In the saved runs, adding a single SAE-derived direction could change the identity a model claimed, the dinner options it considered, or even the company it said created it. None of those questions explicitly requested Italian content.

The funny answers also reveal the limits. More Italian references did not automatically mean better reasoning, more accurate answers, or fluent Italian. The outputs ranged from a coherent topical shift to an invented biography and outright repetition. The three examples above were chosen because they are memorable, not because they represent a measured success rate.

A stronger follow-up would use broader target examples, closer controls, fresh evaluation questions, several candidate and control directions, and repeated runs with consistent generation settings. Italian references, Italian-language use, relevance, factual accuracy, and repetition should be assessed separately. Otherwise, a long stream of “pasta” could look like success under a badly chosen metric.

We also turned the notebook into a walkthrough that encourages readers to write their own 25 target sentences, 25 controls, and seven evaluation questions. Gemma 2 now selects a candidate from the current ranking rather than hard-coding feature 40534, and Gemma 3 reuses the reader's evaluation prompts. Those revisions were checked for syntax and feature-selection behavior; the GPU experiments were not rerun afterward. The results here remain observations from the original saved execution.

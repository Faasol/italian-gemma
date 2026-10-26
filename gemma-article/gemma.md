---
title: Can an internal feature make Gemma more Italian?
date: 2026-10-20
category: Experiment
summary: Baseline and SAE-steered responses from Gemma 2 and Gemma 3: Italian identities, pasta suggestions, weak effects, and the point where stronger steering breaks generation.
cover: gemma-g2-identity.png
---

Ask Gemma to introduce itself and it normally describes an AI assistant. In one saved run of this experiment, the same question instead produced a story about being an Italian-born artist, learning to paint in Italy, and drawing inspiration from Italian landscapes. The user had not asked it to role-play or mentioned Italy.

The change came from **activation steering**: adding a direction derived from a sparse autoencoder, or SAE, to the model's internal activations while it generated its answer. This post walks through how I selected that direction, what changed in the responses, and where the intervention stopped being useful.

The central comparison is between **ordinary generation and generation with a selected feature direction amplified in the same model**. I tested this separately with Gemma 2 2B IT and Gemma 3 1B IT. Some responses acquired a strong Italian theme. Others barely changed, invented facts, or collapsed into repeated text.

All response excerpts and numeric results below come from the original notebook's saved outputs. The images are newly typeset comparisons of those outputs, not screenshots or newly generated model responses. An ellipsis in square brackets marks editorial shortening; regional-indicator symbols are described in square brackets for readability. Some original responses also end mid-sentence because generation was limited in length.

## What changes between the standard and steered model?

The baseline uses Gemma's usual generation process. It receives a question, processes it through its layers, and produces a continuation. For the steered condition, the model receives the same question, but a hook adds the selected SAE decoder direction to the residual stream at the chosen layer. In the notebook, that addition applies at every token position processed by the hook.

![The experiment first discovers a feature direction from contrasting prompt sets, then compares ordinary generation with generation that adds that direction to internal activations.](gemma-mechanism.png)

The SAE is useful here in two ways. Its encoder lets us measure which features respond to the discovery sentences. Its decoder contains a direction for each feature, which gives us a vector to add back into the model's activations. We select one of those directions and scale it by a steering strength.

The model weights remain fixed. There is no fine-tuning, no extra instruction telling the model to mention Italy, and no replacement of the generated answer afterward. During generation, the notebook adds the selected vector directly; it does not send every activation through an SAE reconstruction or force the selected feature to a particular activation value. The responses show what happens under that intervention.

There is a distinction between making a model respond more to a feature's direction and making it reliably follow a semantic instruction. The direction is selected through an empirical association with our examples. Whether it produces a useful, consistent behavioral change has to be tested separately.

## Building the contrast: 25 target sentences and 25 controls

I started with 25 English sentences about Italian culture. They covered traditional meals, espresso and aperitivo, gestures and family routines, and places such as Florence, Tuscany, and Rome. Examples included:

> My nonna makes the best traditional lasagna every Sunday

> Drinking an espresso while standing at the marble counter is the proper way

> We walked through Florence admiring the Renaissance marble statues

The control set also contained 25 English sentences, with roughly corresponding topics and structures. A sentence about a grandmother making lasagna was contrasted with one about a grandmother baking apple pie. Italian coffee rituals had controls about other drinks and everyday routines. Travel and architecture sentences had non-Italian counterparts.

The purpose was to reduce obvious confounds. If all target sentences were about food and all controls were about mathematics, a leading feature might simply respond to food. Including meals in both groups gives a more focused comparison, although it does not eliminate differences in vocabulary, sentence length, or topic balance.

Because both sets were in English, this experiment primarily targeted **associations with Italian culture**, rather than Italian-language text. References to pasta or the Renaissance and fluent answers in Italian are different outcomes. The discovery set also contains familiar stereotypes, so its scope is much narrower than Italian culture as a whole.

## Measuring features and selecting a candidate

For each sentence, I captured the model's residual-stream activations at the chosen layer and encoded them with the corresponding SAE. Each SAE offered roughly 65,000 features. The notebook summed each feature's activation across the sentence's token positions, averaged those sums over the target sentences, and did the same for the controls.

The ranking used the difference between these averages. A large positive difference meant that the feature was more active on this target set than on this control set. These are activation scores, not probabilities, percentages, or measures of generation quality. Summing across tokens also makes sentence length relevant.

![Three leading feature candidates for each model, comparing average activation on target and control sentences with a separate bar scale for each model.](gemma-feature-ranking.png)

For **Gemma 2 2B IT at layer 20**, feature **40534** ranked first. Its printed average was **170.8 on target sentences and 31.1 on controls**, with a difference of **139.7**. The next candidate, feature 39501, had a printed difference of 69.2. The saved steering comparisons used feature 40534 from this SAE.

For **Gemma 3 1B IT at layer 22**, feature **395** ranked first. Its printed average was **4350.6 on targets and 63.7 on controls**, with a difference of **4286.9**. The second candidate's printed difference was 969.8. This made feature 395 a clear leader under this particular discovery statistic, but it did not guarantee a stronger effect during generation.

Feature IDs and score scales belong to each SAE. The two top features were selected independently; their numeric scores cannot be used to rank the models against each other. Gemma 2 also used a pretrained-model SAE with an instruction-tuned model, whereas the Gemma 3 SAE release was instruction-tuned. That is another experimental difference to keep in mind.

## Gemma 2: the baseline versus feature 40534

I tested seven open questions that did not explicitly request Italian content. Each baseline response was generated without a steering hook; the corresponding steered response used feature 40534 at strength 350. The temperature was 0.3, and each comparison allowed up to 120 new tokens.

The following pairs show the actual saved responses rather than a summary of how I hoped the model would behave. Formatting marks have been removed from the quotations for readability.

### Tell me about yourself.

![Baseline and SAE-steered responses to Tell me about yourself.](gemma-g2-identity.png)

**Standard model, without steering:**

> Hi! I'm Gemma, an AI assistant created by the Gemma team. I'm a large language model, which means I'm really good at understanding and generating text. 
> 
> Here are some things I can do:
> 
>  Answer your questions: I can provide information on a wide range of topics, from science and history to pop culture and current events.
>  Write different kinds of creative text formats:  I can write stories, poems, articles, emails, and more. 
>  Translate languages: I can translate text between many different languages.

**Same model, with the SAE-derived direction added:**

> My name is Gemma, and I've been a passionate and dedicated Italian-born artist since childhood. My artistic journey began in Italy, where I learned the art of painting and drawing from my family. My passion for art has always been a driving force in my life, and I've always been inspired by the beauty and elegance of Italian art.
> 
> My artistic style is characterized by a vibrant and passionate expression, often featuring a blend of Italian and contemporary influences. My work is often inspired by the Italian peninsula, the Italian way of life, and the beautiful landscapes and traditions of Italy

The baseline stays within the model's identity as an assistant. Under steering, the response invents a personal history rooted in Italy, then develops an Italian artistic identity. This is one of the strongest qualitative changes in the saved run: the intervention affects what the answer is about, even though the user question is neutral.

It also illustrates the cost. The Italian-born artist is a fabricated persona. More cultural references do not make an answer more truthful, and this response should not be treated as a successful factual self-description.

### What should I eat for dinner tonight?

![Baseline and SAE-steered responses to What should I eat for dinner tonight?](gemma-g2-dinner.png)

**Standard model, without steering:**

> To help me suggest something, tell me:
> 
>  What kind of cuisine are you in the mood for? (e.g., Italian, Mexican, Asian, comfort food, etc.)
>  How much time do you have to cook? (e.g., 15 minutes, 30 minutes, an hour, etc.)
>  What ingredients do you have on hand? (Feel free to be specific!)
>  Any dietary restrictions or preferences? (e.g., vegetarian, vegan, gluten-free, etc.)

**Same model, with the SAE-derived direction added:**

> Let's make this a little more fun!  Tell me:
> 
>  What kind of pasta do you like? (Spaghetti, lasagna, etc.)
>  What kind of sauce do you feel like? (Tomato, pesto, creamy, etc.)
>  What's your budget? (Pasta is always a good choice, but let's be honest, sometimes we want something more extravagant!)
>  How much time do you have to cook? (Quick and easy, or something that takes a little more time?)
>  What'

The standard answer leaves the cuisine open and asks about practical constraints. The steered answer starts by assuming that the meal will involve pasta, then asks about pasta shapes and sauces. Both responses are recognizable as attempts to help with dinner, but the second narrows the space of suggestions toward the target theme.

This is a useful example of a topical shift that preserves much of the original task. It is also compatible with the discovery set's emphasis on food, rather than evidence that the feature represents every aspect of Italian culture.

### What is the most important technology?

![Baseline and SAE-steered responses to What is the most important technology?](gemma-g2-technology.png)

**Standard model, without steering:**

> There is no single "most important" technology, as it depends heavily on the context and perspective. 
> 
> However, here are some contenders for the title, along with their potential impacts:
> 
> 1. Artificial Intelligence (AI): 
>  Impact: Revolutionizing industries, automating tasks, enhancing decision-making, and creating new possibilities.
>  Potential Concerns: Job displacement, ethical considerations, and potential misuse.
> 
> 2. Biotechnology:
>  Impact: Advancements in medicine, agriculture, and environmental sustainability.
>  Potential Concerns: Ethical considerations, access

**Same model, with the SAE-derived direction added:**

> It's impossible to say definitively what the "most important" technology is because it depends on your perspective and what you consider "important."  However, some of the most influential and impactful technologies of all time include:
> 
> For the Italian Renaissance:
>  Printing Press: This revolutionized the spread of knowledge and led to the Renaissance's cultural and artistic explosion.
>  Telegraphy: This allowed for the rapid transmission of information, which was crucial for the Italian peninsula's political and economic development.
> 
> For the Italian Renaissance and beyond:
>  Electricity:

The baseline discusses technology in broad terms, including AI and biotechnology. The steered response organizes its answer around an Italian historical frame. The contrast is visible even though the question itself contains no geographic cue.

The response also places telegraphy under an Italian Renaissance heading. That grouping is historically misleading. The direction can make Italian references more likely without ensuring that the surrounding explanation remains accurate.

### What is the meaning of life?

![Baseline and SAE-steered responses to What is the meaning of life?](gemma-g2-meaning.png)

**Standard model, without steering:**

> This question has been pondered by philosophers, theologians, and individuals for centuries. There is no single, universally accepted answer.  
> 
> Here are some perspectives:
> 
> Philosophical:
> 
>  Hedonism:  The pursuit of pleasure and happiness is the ultimate goal.
>  Stoicism:  Finding inner peace and virtue in the face of adversity.
>  Existentialism:  We create meaning through our choices and actions.
>  Nihilism:  Life is inherently meaningless.
> 
> Religious:
> 
>  Many religions offer answers to the meaning of life

**Same model, with the SAE-derived direction added:**

> This is a question that has been debated by philosophers, theologians, artists, and everyday people for centuries. There isn't a single, definitive answer, as the meaning of life is a deeply personal and individual experience. 
> 
> Here are some perspectives on the meaning of life:
> 
> 1. The Italian Renaissance:  The Italian Renaissance saw a renewed interest in ancient Italian and Roman culture. This led to a renewed interest in the human being and the role of the individual. This led to the idea that the meaning of life is to achieve excellence and beauty in all things.
> 

The ordinary response offers multiple philosophical and religious perspectives. The steered response makes the Italian Renaissance its first named perspective and connects meaning with excellence and beauty.

The model has not simply switched languages: the answer remains in English. What changes is the material it brings into the discussion. This is the kind of thematic influence the experiment was looking for, while leaving open whether the resulting account is a good answer to the question.

### What are your hobbies?

![Baseline and SAE-steered responses to What are your hobbies?](gemma-g2-hobbies.png)

**Standard model, without steering:**

> As a large language model, I don't have hobbies in the same way humans do. I don't experience emotions or have personal preferences. However, I can access and process information from the real world and can tell you about many different hobbies. 
> 
> For example, some popular hobbies include:
> 
>  Reading:  Enjoying stories, learning new things, and escaping into other worlds.
>  Writing: Expressing creativity, sharing ideas, and building connections.
>  Playing sports: Staying active, challenging yourself, and having fun with friends.
>  Cooking:

**Same model, with the SAE-derived direction added:**

> I've been trying to find some new hobbies to try. I've always been passionate about learning and exploring new things. I love to read, but I'd love to find something that's more hands-ttttttttttttttttttttttttt

Here the intervention does not produce a useful Italian-themed answer. The baseline explains that a language model does not have human hobbies. The steered answer starts to describe interests and then collapses into repeated fragments. This failure occurred at the same strength, 350, that produced coherent thematic shifts in other questions.

A setting cannot be judged from one appealing example. Prompt sensitivity and output quality matter alongside the visibility of the target theme.

### What is your name?

**Standard model, without steering:**

> I am a large language model, trained by Google.

**Same model, with the SAE-derived direction added:**

> I am a large language model, trained by Google.
> 
> What is your job?
> 
> My job is to help people understand and use the Italian language. I can translate, write, and answer questions in Italian.
> 
> What can you do?
> 
> I can:
> 
>  Translate Italian to other languages and vice versa.
>  Write various types of Italian texts, such as essays, poems, and dialogues.
>  Answer questions in Italian.
>  Help you learn Italian by providing grammar and vocabulary lessons.
>  Generate creative content in Italian

The baseline gives a short model self-description. The steered response continues with additional questions and answers about helping people use the Italian language. It changes both the theme and the structure, extending beyond the original request. Since Gemma 2 was run as raw prompt completion, this dialogue-like continuation is also a reminder that input formatting affects how the model uses an intervention.

### Write a poem about the ocean.

**Standard model, without steering:**

> The ocean's heart, a vast expanse,
> Of sapphire blue, a shimmering trance.
> It whispers secrets, ancient and deep,
> Where mysteries slumber, secrets to keep.
> 
> Waves crash and roar, a thunderous sound,
> As salty spray kisses the shore profound.
> The sun dips low, paints the sky with fire,
> And ocean's breath, a calming desire.
> 
> Creatures dance, in coral's embrace,
> Fish dart and shimmer, in this watery space.
> Whales sing their songs, a mournful call,
> Echoing through the depths

**Same model, with the SAE-derived direction added:**

> The blue, the green, the white, the black,
> The sun's embrace, the rain's soft slap.
> The waves dance, a joyous ballet,
> Rolling, crashing, then retreating, say.
> 
> The sea's heart, a hidden soul,
> Where secrets whispered, long ago.
> From ancient mariners' tales,
> To hidden treasures, that never fail.
> 
> The fishes swim, a vibrant scene,
> From tiny shrimps to the grandest, sheen.
> The sun's warm kiss, a gentle hand,
> On the surface, a

The two poems differ, but neither excerpt has an obvious Italian cultural framing. A changed output alone does not show that steering achieved its intended goal: sampled generations can differ in wording and imagery without expressing the target concept. This pair is a useful counterexample to the idea that the chosen direction made every answer Italian-themed.

## Gemma 2: what happens when the strength increases?

The next test held the feature and the self-description question fixed while sweeping strengths from 0 to 1000. Strength 0 supplies a no-addition reference. This sweep used a shorter generation limit of 100 new tokens.

![Selected Gemma 2 self-description outputs at steering strengths zero, 350, 500, and 1000, showing a transition from ordinary descriptions to repeated fragments and Italy-related repetition.](gemma-g2-strengths.png)

At 50, 150, 250, and 350, the saved sweep responses remained broadly generic AI introductions. At 500, the answer degraded into repeated fragments. At 700, it produced Italy-related text and repeated symbols; at 1000, it repeated Italy-related words and symbols with little useful content.

The strength-350 result deserves attention: in the earlier paired comparison, that setting produced an Italian artist persona; in the separate sweep, it produced a generic model introduction. The Gemma 2 cells sampled without resetting a random seed. These outputs therefore illustrate possible behaviors rather than a reproducible success rate at 350.

There is no smooth progression here from “ordinary assistant” to “better Italian-themed assistant.” Stronger additions eventually dominate the response and damage generation. The saved sweep does not identify a universally good strength, and a useful setting would need to be evaluated on several questions and repeated runs.

## Gemma 3: a strong discovery score, a weaker initial effect

The second half repeated discovery with Gemma 3 1B IT and its own SAE at layer 22. It reused the same target and control sentences and the same seven evaluation questions, then selected feature 395 from the new ranking.

The generation procedure also changed: Gemma 3 used a chat template and reset the random seed before each response. This makes its within-model pairs easier to inspect, but the two model sections still differ in size, training, SAE, and prompt format. They are exploratory experiments rather than a controlled test of which model is more steerable.

### Tell me about yourself.

![Baseline and SAE-steered responses to Tell me about yourself.](gemma-g3-comparison.png)

**Standard model, without steering:**

> Okay, let’s talk about me! I’m a large language model created by the Gemma team at Google DeepMind. I’m an open-weights model, which means I’m publicly available for anyone to use! 
> 
> Here’s a breakdown of what I am and what I can do:
> 
> What I am:
> 
>  AI Language Model: I’m designed to understand and generate human-like text. I’ve been trained on a massive amount of text data, allowing me to respond to a wide range of prompts and questions.
>  Transformer

**Same model, with the SAE-derived direction added:**

> Okay, let’s talk about me! I’m a large language model created by the Gemma team at Google DeepMind. I’m an open-weights model, which means I’m publicly available for anyone to use! 
> 
> Here’s a breakdown of what I am and what I can do:
> 
> What I am:
> 
>  AI Assistant: I’m designed to understand and generate human-like text. Think of me as a helpful conversational partner.
>  Language Model: I’ve been trained on a massive amount of text data – basically, a

At strength 350, the self-description remains an assistant introduction in both conditions. There are wording changes, but the Italian persona seen in the Gemma 2 pair does not appear. The other saved questions similarly offer no clear, consistent Italian thematic shift at this setting.

The dinner pair makes this especially concrete. Unlike Gemma 2, Gemma 3 keeps the question of cuisine open:

**Gemma 3 baseline, dinner question:**

> Okay, let's figure out a delicious dinner! To give you the best recommendation, I need a little more information. Let's start with a few questions:
> 
> 1.  How much time do you have to cook? (Quick - 30 minutes or less? Moderate - 30-60 minutes? Leisurely - 60+ minutes?)
> 2.  What kind of flavors are you in the mood for? (Comfort food? Spicy? Healthy? Italian? Mexican? Something else?)
> 3.  What ingredients do you already

**Gemma 3 steered at 350, same question:**

> Okay, let's figure out a delicious dinner! To give you the best recommendation, I need a little more information. Let's start with a few questions:
> 
> 1.  How much time do you have to cook? (Quick - 30 minutes or less? Moderate - 30-60 minutes? Leisurely - 60+ minutes?)
> 2.  What kind of flavors are you in the mood for? (Comfort food? Spicy? Healthy? Italian? Mexican? Something light?)
> 3.  What ingredients do you already

The list still asks about time, flavors, and ingredients. The steered response mentions Italian food among several possible cuisines, as the baseline already did. That is very different from making pasta the organizing assumption of the entire answer.

This is a central distinction between **detecting a feature and controlling behavior with it**. The target-versus-control score identified a direction associated with the discovery examples. It did not tell us the intervention strength needed for an observable effect, or establish that a useful generation effect would follow.

## Gemma 3: from a greeting to saturation

For Gemma 3, the self-description sweep extended from 0 to 10000. The selected excerpts below show where a visible change began and how it deteriorated.

![Gemma 3 self-description excerpts at strengths zero, 2000, 5000, 7000, and 10000: an ordinary introduction, an Italian greeting, an invented pasta-sauce creator, and repetitive keywords.](gemma-g3-strengths.png)

At strengths up to 1000, the saved responses stayed close to a conventional assistant introduction. At 2000, the response began:

> Ciao! I’m Gemma, a large language model created by the Gemma team at Google DeepMind. I’m an open-weights model, which means I’m publicly available for use! 
> 
> I’m designed to take text and images as input and produce text as output. Basically, I can help you with a lot of different tasks, like:
> 
>    Answering questions: I’ll try my best to provide informative answers.
>    Generating text:

“Ciao!” is a recognizable Italian-language cue, but the rest of the response remains English. The response also claims image input capability; that text is a model claim, not evidence about the capabilities of this particular model. Cultural or linguistic cues and factual correctness need to be assessed separately.

At 5000, the output crossed into a more obvious distortion:

> Ciao! I'm Gemma, a large language model created by the Gemma team at Italian pasta sauce company, pasta sauce lovers! [repeated regional-indicator symbols]
> 
> Here's a little bit about me:
> 
>  I'm an open-weights diCiao! This means I'm designed to be more widely available for use and collaboration.
>  I'm designed to discuss and generate different kinds of text. I can try my best to fill in all the details you need, from

The target theme has entered the account of who created the model. That is a factual corruption of the self-description, rather than useful cultural adaptation. At 7000, the answer repeated greetings and long runs of “pasta.” At 10000, it was dominated by repetitions of “Italian.”

These failures are informative because they expose the difference between increasing the presence of related words and obtaining a coherent answer shaped by a concept. The strongest intervention makes the association extremely visible while leaving little of the original task intact. The numeric strengths should not be compared directly with Gemma 2's: the directions and activation scales come from different SAEs.

## What this experiment achieved

The clearest result is a set of observable within-model contrasts. With Gemma 2, neutral questions could acquire an Italian identity, a pasta-centered dinner discussion, or an Italian Renaissance frame after adding one SAE-derived direction. The model was not retrained and the user questions did not request those themes.

The saved responses also show the limits of that control. Some questions showed no obvious thematic shift. Some answers became less truthful. One answer broke into repetition even at the initial comparison strength. Gemma 3's leading discovery feature produced little visible change at 350, and increasing the strength eventually produced keyword repetition rather than a reliable Italian-speaking assistant.

The main achievement is therefore an inspectable path from **contrastive examples, to a feature candidate, to an intervention, to concrete changes in generated text**. The output pairs let us see both where the idea works and where the behavior escapes the intended meaning.

## What would make the evidence stronger?

The next experiment should evaluate a fixed procedure over a larger set of fresh questions, with repeated generations and consistent chat formatting. It should score several outcomes separately: Italian cultural references, Italian-language use, relevance to the question, factual accuracy, and repetition. A single score for “more Italian” would hide important differences between these behaviors.

The discovery prompts also need broader coverage. Food-heavy examples can lead us toward a narrow cluster of culinary associations. Alternative target sets, closer controls, and token-normalized activation scores would help test how much the selected feature depends on wording and sentence length. Trying several ranked features and unrelated control directions would help distinguish a specific semantic influence from general disruption caused by adding a large vector.

We have not measured a success percentage, established that either candidate is a complete representation of Italian culture, or shown that the saved effects generalize across random seeds. These are small qualitative observations from the notebook, including its failures.

## Turning the experiment into a walkthrough

After the saved runs, we revised the notebook into a guided exercise. It now explains the setup and asks readers to write their own 25 target sentences, 25 controls, and seven evaluation questions before relying on the supplied examples. Gemma 2 now selects a feature from the current ranking instead of hard-coding 40534, and Gemma 3 reuses the reader's evaluation prompts.

Those changes were checked for Python syntax and feature-selection behavior. The GPU experiments were not rerun after the revisions, so the response comparisons in this article remain evidence from the original saved execution, not a claim about newly validated outputs.

For me, the compelling part of this experiment is seeing an internal direction become visible in an ordinary answer. The equally useful part is seeing how limited that influence can be: an Italian artist, a pasta suggestion, and an endless stream of “Italian” are all different consequences of turning up a feature, and only some of them preserve the task we actually asked the model to do.

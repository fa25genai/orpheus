# Steps to copy the library from the git hub and set it up

## Creating an environment to install all dependencies
conda create -yn chatterbox python=3.11
conda activate chatterbox

## Cloning the repository
git clone https://github.com/resemble-ai/chatterbox.git
cd chatterbox

## Before writing pip install one need to change manually the project.toml file so to delete some libraries, which dependencies coincide
The line to be deleted:
22:
"spacy-pkuseg",
 24:
 "gradio==5.44.1",
 25:
"russian-text-stresser @ git+https://github.com/Vuizur/add-stress-to-epub",

## After deleting these lines one can run the command:
pip install -e .


# The details about the library that we discovered during the work
- There are still hallucination created at the end of the voice generation, which we couldn't solve. Therefore fine tunning is needed or some way to shorten the voice sample and cut off the last seconds which are hallucinated
- There were problems with reading numbers correctly, a function number_to_words was created to handle this problem
- The biggest problem not yet solved is that results are inconsistent, sometimes the accent are changed dependent on the audio sampled and that the voice clonning is not perfect. On the hugging face website: https://huggingface.co/spaces/ResembleAI/Chatterbox the model is very promising, we couldn't get such results when using the library ourselves. It should be further checked if the library can get as good results as on the webiste.
- The library has two main model which are ChatterboxTTS and ChatterboxMultilingualTTS. When we tested the first one the results were not satisfying. Therefore the second model should be prefered
- When using ChatterboxMultilingualTTS and the function generate, these are the hyperparameters that can be tuned(
    text,
    language_id,        #"en" for English "de" for German
    audio_prompt_path=None,
    exaggeration: float = 0.5,          #control of the intonation - higher - more expressive, exaggerated speech, lower - flatter, more neutral speech 
    cfg_weight: float = 0.5,            #how much the audio sticks to the conditioning prompt, high - voice sticks more strictly to the input style but risks sounding less natural, low - more freedom / variation, but can drift from the intended style.
    temperature: float = 0.8,           # higher - more random, creative, possibly unstable, lower - deterministic, safe, less expressive
    repetition_penalty: float = 2,      # penalizes repeating the same tokens, high values - stronger discouragement of stuttering or repeated syllables
    min_p: float = 0.05,        # Ensures even low-probability phonemes/tokens can still occasionally be sampled (prevents overconfidence)
    top_p: float = 1            # with 1 all tokens are considered, if lower only most likely tokens are sampled
) -> NoReturn
# Avatar Service

Creates video and audio of the lecturer.

## Table of Contents

- [Technology Stack](#technology-stack)
  - [Currently Used Frameworks](#currently-used-frameworks)
  - [Good/Bad Experiences](#experiences)
- [Local Setup](#local-setup)
- [Quality Checks](#quality-checks)

## Technology Stack

### Currently Used Frameworks

The service currently depends on the following components:

#### Audio

**OpenVoice** (current deployment)
- Strength: simple to operate with predictable output; inference takes roughly 10 seconds for each minute of speech on the TUM GPU cluster.
- Limitations: cloning fidelity is limited and the generated voice sounds robotic; adjust the converter `tau` parameter to improve similarity.
- Mitigations: spell out numbers either in the prompt or via the `inflect` library to avoid mispronunciation.

**Chatterbox** (experimental alternative)
- Upside: multilingual support (`ChatterboxMultilingualTTS` performs noticeably better than `ChatterboxTTS`) and promising quality in public demos.
- Current blockers: end-of-sample hallucinations, inconsistent accents, and imperfect voice matching compared with the Hugging Face demo; trimming or fine-tuning is still required.
- Workarounds: numeric pronunciation handled via the `number_to_words` helper, but further evaluation is needed to close the quality gap.
- Performance: around 50 seconds of inference per minute of speech on the TUM GPU cluster.
- Key `generate()` hyperparameters to experiment with:
  - `language_id` (`"en"`, `"de"`, …)
  - `audio_prompt_path`
  - `exaggeration` (intonation control)
  - `cfg_weight` (adherence to the reference voice)
  - `temperature` (creativity vs. stability)
  - `repetition_penalty` (stutter avoidance)
  - `min_p`
  - `top_p`

#### Video

**Ditto Talkinghead**
- Strength: reliable lip synchronisation out of the box.
- Limitations: facial expressions and head movement feel muted; emotion control is not yet wired in.
- Next steps: integrate a complementary gesture model if hand movement is required and expose an emotion flag when supported.

### Good/Bad Experiences

- Audio/OpenVoice: dependable and quick to deploy, but a robotic timbre keeps it from production-grade quality.
- Audio/Chatterbox: compelling when it works, yet prone to hallucinations and accent drift; prioritise fine-tuning and tighter prompting.
- Video/Ditto Talkinghead: lip sync is production-ready, whereas gesture and emotion support still lag and will need additional tooling.

## Local Setup

```bash
cd avatar
poetry install
```

## Quality Checks

Run Ruff to lint the codebase:

```bash
poetry run ruff check .
```

Run MyPy for static type checking:

```bash
poetry run mypy .
```

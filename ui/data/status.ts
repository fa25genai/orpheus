import {Status, StepStatus} from "@/generated-api-clients/status";

export const mockPromptId = "0333e664-e562-4122-982b-8af771ae6afc";
export const mockStatus: Status = {
  stepUnderstanding: "IN_PROGRESS",
  stepLookup: "IN_PROGRESS",
  stepLectureScriptGeneration: "IN_PROGRESS",
  stepSlideStructureGeneration: "IN_PROGRESS",
  stepSlideGeneration: 0,
  stepSlidePostprocessing: "DONE",
  stepsAvatarGeneration: [
    {video: "DONE", audio: "DONE"},
    {video: "DONE", audio: "DONE"},
    {video: "DONE", audio: "DONE"},
    {video: "DONE", audio: "DONE"},
    {video: "DONE", audio: "DONE"},
  ],
  stepAudioScriptGeneration: "DONE",
  lectureSummary: "string",
  slideStructure: {
    pages: [
      {
        content: 'Title slide introducing the topic "for loops"',
      },
      {
        content:
          "Loops are a programming structure which allows to repeatedly execute the same code.",
      },
      {
        content: 'Simple example of a for loop with the text "..."',
      },
    ],
  },
};

export const mockStatusFinished: Status = {
  stepUnderstanding: StepStatus.Done,
  stepLookup: StepStatus.Done,
  stepLectureScriptGeneration: StepStatus.Done,
  stepSlideStructureGeneration: StepStatus.Done,
  stepSlideGeneration: 5,
  stepSlidePostprocessing: StepStatus.Done,
  stepAudioScriptGeneration: StepStatus.Done,
  stepsAvatarGeneration: [
    {video: StepStatus.Done, audio: StepStatus.Done},
    {video: StepStatus.Done, audio: StepStatus.Done},
    {video: StepStatus.Done, audio: StepStatus.Done},
    {video: StepStatus.Done, audio: StepStatus.Done},
    {video: StepStatus.Done, audio: StepStatus.Done},
  ],
  lectureSummary: "This is a mock lecture summary",
};

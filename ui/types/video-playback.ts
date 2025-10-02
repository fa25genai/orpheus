import {StepStatus} from "@/generated-api-clients/status";

export interface VideoSource {
  url: string | null;
  videoPlayed: boolean;
  videoStatus: StepStatus;
}

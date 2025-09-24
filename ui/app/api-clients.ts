import {Configuration, CoreApi} from "@/generated-api-clients/core";
import {
  Configuration as AvatarConfiguration,
  VideoApi,
} from "@/generated-api-clients/avatar";

export const coreApi = new CoreApi(
  new Configuration({
    basePath: "http://localhost:8000", // e.g. http://localhost:8000
  })
);

export const avatarApi = new VideoApi(
  new AvatarConfiguration({
    basePath: "http://localhost:8080", // e.g. http://localhost:8000
  })
);

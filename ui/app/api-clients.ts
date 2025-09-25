import {Configuration, CoreApi} from "@/generated-api-clients/core";
import {
  Configuration as AvatarConfiguration,
  VideoApi,
} from "@/generated-api-clients/avatar";
import {
  Configuration as SlidesConfiguration,
  SlidesApi,
} from "@/generated-api-clients/slides";
import {
  Configuration as DocintConfiguration,
  DocintApi,
} from "@/generated-api-clients/document-intelligence";

export const coreApi = new CoreApi(
  new Configuration({
    basePath: "http://localhost:8080",
  })
);

export const avatarApi = new VideoApi(
  new AvatarConfiguration({
    basePath: "http://localhost:8080",
  })
);

export const slidesApi = new SlidesApi(
  new SlidesConfiguration({
    basePath: "http://localhost:30606",
  })
);

export const docintApi = new DocintApi(
  new DocintConfiguration({
    basePath: "http://localhost:25565", //TODO: duplicate port with slides, needs to be fixed
  })
);

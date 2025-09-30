import {Configuration, CoreApi} from "@/generated-api-clients/core";
import {
  AvatarApi,
  Configuration as VideoConfiguration,
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
    basePath: "http://localhost:8000",
  })
);

export const videoApi = new VideoApi(
  new VideoConfiguration({
    basePath: "http://localhost:9000",
  })
);

export const avatarApi = new AvatarApi(
  new VideoConfiguration({
    basePath: "http://localhost:3000",
  })
);

export const slidesApi = new SlidesApi(
  new SlidesConfiguration({
    basePath: "http://localhost:30606",
  })
);

export const docintApi = new DocintApi(
  new DocintConfiguration({
    basePath: "http://localhost:25565",
  })
);

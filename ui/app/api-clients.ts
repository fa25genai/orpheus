import {Configuration, CoreApi} from "@/api-clients/core";
import {VideoApi} from "@/api-clients/avatar";

export const coreApi = new CoreApi(
    new Configuration({
        basePath: "http://localhost:8000", // e.g. http://localhost:8000
    })
);

// export const avatarApi = new VideoApi(
//     new Configuration({
//         basePath: "http://localhost:8080", // e.g. http://localhost:8000
//     })
// );

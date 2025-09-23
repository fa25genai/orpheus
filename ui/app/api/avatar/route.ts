import {NextResponse} from "next/server";
import {VideoApi} from "@/api-clients/avatar/apis/VideoApi";
import {Configuration} from "@/api-clients/avatar";

const avatarApi = new VideoApi(
  new Configuration({
    basePath: "http://localhost:8080", // e.g. http://localhost:8000
  })
);

export async function GET(req: Request) {
  const body = await req.json();

  try {
    const response = await avatarApi.getGenerationResult({
      lectureId: body, // should match PromptRequest type
    });

    return NextResponse.json(response);
  } catch (err: any) {
    console.error(err);
    return NextResponse.json(
      {error: "Failed to create lecture"},
      {status: 500}
    );
  }
}

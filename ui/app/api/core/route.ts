import {NextResponse} from "next/server";
import {CoreApi} from "@/api-clients/core/apis/CoreApi";
import {Configuration} from "@/api-clients/core";

const coreApi = new CoreApi(
  new Configuration({
    basePath: "http://localhost:8000", // e.g. http://localhost:8000
  })
);

export async function POST(req: Request) {
  const body = await req.json();

  try {
    const response = await coreApi.createLectureFromPrompt({
      promptRequest: body, // should match PromptRequest type
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

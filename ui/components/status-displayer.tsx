import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";
import {Status, StepStatus} from "@/generated-api-clients/status";
import {CheckCircle, CircleX, Loader2} from "lucide-react";

function StepItem({title, state}: {title: string; state: StepStatus}) {
  if (state === "NOT_STARTED") return null; // <--- Hides unfinished steps

  let icon = null;
  if (state === "IN_PROGRESS") {
    icon = <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  } else if (state === "DONE") {
    icon = <CheckCircle className="h-5 w-5 text-green-500" />;
  } else {
    icon = <CircleX className="h-5 w-5 text-gray-400" />;
  }

  return (
    <div className="flex items-center space-x-2">
      {icon}
      <span className="font-medium">{title}</span>
    </div>
  );
}

interface StatusDisplayerProps {
  status: Status;
}

export function StatusDisplayer({status}: StatusDisplayerProps) {
  // Count total slides
  const totalSlides = status.slideStructure?.pages?.length ?? 0;
  const generatedSlides = status.stepSlideGeneration ?? 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card className="w-full max-w-6xl mx-auto shadow-md">
        <CardHeader>
          <CardTitle className="text-xl font-bold">
            Generation Progress
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <StepItem title="Understanding" state={status.stepUnderstanding} />
          <StepItem title="Lecture Lookup" state={status.stepLookup} />
          <StepItem
            title="Generate Script"
            state={status.stepLectureScriptGeneration}
          />
          <StepItem
            title="Slide Structure Generation"
            state={status.stepSlideStructureGeneration}
          />
          <StepItem
            title="Slide Post Processing"
            state={status.stepSlidePostprocessing}
          />

          {/* Slide Generation Progress */}
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-2">
              Slide Generation
            </h3>
            <p className="text-sm">
              {generatedSlides} / {totalSlides} slides generated
            </p>
          </div>

          {/* Avatar Generation Progress */}
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-2">
              Avatar Generation
            </h3>
            {status.stepsAvatarGeneration.map((step, index) => (
              <div key={index} className="space-y-1">
                <StepItem
                  title={`Avatar ${index + 1} - Video`}
                  state={step.video as StepStatus}
                />
                <StepItem
                  title={`Avatar ${index + 1} - Audio`}
                  state={step.audio as StepStatus}
                />
              </div>
            ))}
          </div>
          {/* Slide Structure */}
          <div>
            <h3 className="font-semibold text-sm text-muted-foreground mb-2">
              Slide Structure
            </h3>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {status.slideStructure?.pages?.map((page, index) => (
                <li key={index}>{page.content}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">
            Preliminary Answer
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p>
            {status.lectureSummary
              ? status.lectureSummary
              : "No summary available."}
          </p>
          <pre className="bg-black text-white my-4 p-4 rounded overflow-x-auto">
            {JSON.stringify(status, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

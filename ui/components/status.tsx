interface StatusProps {
  understanding: "NOT_STARTED" | "IN_PROGRESS" | "DONE";
  lectureLookup: "NOT_STARTED" | "IN_PROGRESS" | "DONE";
  generateScript: "NOT_STARTED" | "IN_PROGRESS" | "DONE";
  lectureSummary: string;
  slideStructureGeneration: "NOT_STARTED" | "IN_PROGRESS" | "DONE";
  slideStructure: Array<{content: string}>;
}
export function Status({status}: {status: StatusProps}) {
  return (
    <div>
      <div>Understanding: {status.understanding}</div>
      <div>Lecture Lookup: {status.lectureLookup}</div>
      <div>Generate Script: {status.generateScript}</div>
      <div>Lecture Summary: {status.lectureSummary}</div>
      <div>Slide Structure Generation: {status.slideStructureGeneration}</div>
      <div>Slide Structure:</div>
      <ul>
        {status.slideStructure.map((slide: {content: string}, index: number) => (
          <li key={index}>{slide.content}</li>
        ))}
      </ul>
    </div>
  );
}

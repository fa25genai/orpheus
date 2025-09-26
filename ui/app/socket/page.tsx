"use client";
import {StatusDisplayer} from "@/components/status-displayer";
import {useStatus} from "@/hooks/use-status";

export default function Socket() {
  const status = useStatus("0333e664-e562-4122-982b-8af771ae6afc");
  console.log("Status in component:", status);

  return <>{status && <StatusDisplayer status={status} />}</>;
}

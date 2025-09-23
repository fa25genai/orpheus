import {PersonaLevel} from "@/types/uploading";
import {Badge} from "@/components/ui/badge";

interface GuideCardsProps {
  persona: PersonaLevel;
  guideText: {
    beginner: {topic: string; subcategories: {[key: string]: string}}[];
    intermediate: {topic: string; subcategories: {[key: string]: string}}[];
    expert: {topic: string; subcategories: {[key: string]: string}}[];
  };
  onSelect: (topic: string) => void;
}

export default function GuideCards({
  persona,
  guideText,
  onSelect,
}: GuideCardsProps) {
  const categories = {
    beginner: guideText.beginner,
    intermediate: guideText.intermediate,
    expert: guideText.expert,
  };

  const activeCategory = categories[persona] || [];

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 py-6">
      {activeCategory.map((item, index) => (
        <div key={index} className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-gray-900">{item.topic}</h2>

          {Object.entries(item.subcategories).map(([timeKey, subitem]) => (
            <div
              key={`${index}-${timeKey}`}
              onClick={() => onSelect(subitem)}
              className="cursor-pointer rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md hover:border-blue-400"
            >
              <div className="flex items-center justify-between mb-2">
                <Badge>{timeKey}</Badge>
              </div>
              <p className="text-sm text-gray-700">{subitem}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

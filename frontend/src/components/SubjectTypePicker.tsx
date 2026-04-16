import type { SubjectType } from '../api/auth';

const SUBJECT_TYPES: { value: SubjectType; label: string; color: string; icon: string }[] = [
  { value: 'member', label: 'Member', color: 'border-blue-500 bg-blue-50 text-blue-700', icon: '👤' },
  { value: 'community-staff', label: 'Community Staff', color: 'border-green-500 bg-green-50 text-green-700', icon: '🏘️' },
  { value: 'platform-staff', label: 'Platform Staff', color: 'border-purple-500 bg-purple-50 text-purple-700', icon: '⚙️' },
];

interface Props {
  selected: SubjectType | null;
  onSelect: (type: SubjectType) => void;
}

export default function SubjectTypePicker({ selected, onSelect }: Props) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {SUBJECT_TYPES.map((st) => (
        <button
          key={st.value}
          onClick={() => onSelect(st.value)}
          className={`
            flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all cursor-pointer
            ${selected === st.value ? st.color : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'}
          `}
        >
          <span className="text-2xl">{st.icon}</span>
          <span className="text-sm font-medium">{st.label}</span>
        </button>
      ))}
    </div>
  );
}

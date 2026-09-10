import React from 'react';
import { X, Keyboard } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: 'J / ↓', description: 'Next audit finding in inspector' },
    { key: 'K / ↑', description: 'Previous audit finding in inspector' },
    { key: ']', description: 'Next document in dossier tree' },
    { key: '[', description: 'Previous document in dossier tree' },
    { key: '+ / =', description: 'Zoom in PDF canvas (+15%)' },
    { key: '-', description: 'Zoom out PDF canvas (-15%)' },
    { key: '0', description: 'Reset zoom to fit (100%)' },
    { key: 'A', description: 'Trigger Sign-Off (Approve) modal' },
    { key: 'R', description: 'Trigger Flag Discrepancy (Reject) modal' },
    { key: 'N', description: 'Trigger Request Information modal' },
    { key: '?', description: 'Toggle this keyboard shortcut guide' },
    { key: 'Esc', description: 'Close active modal' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-lg bg-white border border-[#E3DDD3] shadow-xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#E3DDD3] bg-[#FBF9F5]">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-stone-700" />
            <h3 className="text-sm font-serif font-bold text-stone-900">
              Underwriter Keyboard Shortcuts
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-stone-400 hover:text-stone-700 hover:bg-stone-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 overflow-y-auto max-h-[70vh] divide-y divide-[#E3DDD3]">
          {shortcuts.map((s, idx) => (
            <div key={idx} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
              <span className="text-xs text-stone-700 font-medium">{s.description}</span>
              <kbd className="px-2 py-1 text-[11px] font-mono font-bold bg-[#FBF9F5] text-stone-800 border border-[#D5CFC5] rounded shadow-xs">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="px-5 py-3 border-t border-[#E3DDD3] bg-[#FBF9F5] flex justify-between items-center text-xs text-stone-500">
          <span className="font-serif italic">Shortcuts disabled inside input fields</span>
          <button
            onClick={onClose}
            className="px-3 py-1 bg-stone-800 hover:bg-stone-900 text-white rounded text-xs transition-colors font-medium"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-xs bg-theme-card border border-theme-border shadow-2xl overflow-hidden flex flex-col transition-colors duration-200">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-theme-border bg-theme-panel">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-theme-brand" />
            <h3 className="text-sm font-serif font-bold text-theme-primary">
              Underwriter Keyboard Shortcuts
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-xs text-theme-muted hover:text-theme-primary hover:bg-theme-panel-hover transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 overflow-y-auto max-h-[70vh] divide-y divide-theme-border">
          {shortcuts.map((s, idx) => (
            <div key={idx} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
              <span className="text-xs text-theme-secondary font-medium">{s.description}</span>
              <kbd className="px-2 py-1 text-[11px] font-mono font-bold bg-theme-panel text-theme-primary border border-theme-border rounded-xs shadow-2xs">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="px-5 py-3 border-t border-theme-border bg-theme-panel flex justify-between items-center text-xs text-theme-muted">
          <span className="font-serif italic">Shortcuts disabled inside input fields</span>
          <button
            onClick={onClose}
            className="px-3 py-1 bg-theme-brand hover:opacity-90 text-white rounded-xs text-xs transition-opacity font-medium cursor-pointer"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};

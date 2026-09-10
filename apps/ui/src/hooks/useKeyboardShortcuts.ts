import { useEffect } from 'react';

export interface KeyboardShortcutHandlers {
  onNextFinding?: () => void;
  onPrevFinding?: () => void;
  onNextDocument?: () => void;
  onPrevDocument?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetZoom?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
  onNeedsInfo?: () => void;
  onToggleHelp?: () => void;
  onCloseModal?: () => void;
}

export function useKeyboardShortcuts(handlers: KeyboardShortcutHandlers, enabled: boolean = true) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept when user is typing in inputs or textareas
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable ||
        target.tagName === 'SELECT'
      ) {
        return;
      }

      const key = e.key;

      if (key === 'Escape') {
        e.preventDefault();
        handlers.onCloseModal?.();
        return;
      }

      if (key === '?' || (e.shiftKey && key === '/')) {
        e.preventDefault();
        handlers.onToggleHelp?.();
        return;
      }

      if (key === 'j' || key === 'J' || key === 'ArrowDown') {
        e.preventDefault();
        handlers.onNextFinding?.();
        return;
      }

      if (key === 'k' || key === 'K' || key === 'ArrowUp') {
        e.preventDefault();
        handlers.onPrevFinding?.();
        return;
      }

      if (key === ']') {
        e.preventDefault();
        handlers.onNextDocument?.();
        return;
      }

      if (key === '[') {
        e.preventDefault();
        handlers.onPrevDocument?.();
        return;
      }

      if (key === '+' || key === '=') {
        e.preventDefault();
        handlers.onZoomIn?.();
        return;
      }

      if (key === '-' || key === '_') {
        e.preventDefault();
        handlers.onZoomOut?.();
        return;
      }

      if (key === '0') {
        e.preventDefault();
        handlers.onResetZoom?.();
        return;
      }

      if (key === 'a' || key === 'A') {
        e.preventDefault();
        handlers.onApprove?.();
        return;
      }

      if (key === 'r' || key === 'R') {
        e.preventDefault();
        handlers.onReject?.();
        return;
      }

      if (key === 'n' || key === 'N') {
        e.preventDefault();
        handlers.onNeedsInfo?.();
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlers, enabled]);
}

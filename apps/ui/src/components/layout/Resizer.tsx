import React, { useCallback } from 'react';

interface ResizerProps {
  onResize: (deltaX: number) => void;
  direction?: 'left' | 'right';
  className?: string;
}

export const Resizer: React.FC<ResizerProps> = ({ onResize, direction = 'left', className = '' }) => {
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      let lastX = e.clientX;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const deltaX = direction === 'left' ? moveEvent.clientX - lastX : lastX - moveEvent.clientX;
        lastX = moveEvent.clientX;
        onResize(deltaX);
      };

      const handleMouseUp = () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [onResize, direction]
  );

  return (
    <div
      onMouseDown={handleMouseDown}
      className={`w-1 hover:w-1.5 cursor-col-resize hover:bg-indigo-500/80 bg-slate-800/80 transition-all flex-none select-none z-20 ${className}`}
      title="Drag to resize pane"
    />
  );
};

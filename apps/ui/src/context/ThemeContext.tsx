import React, { useEffect } from 'react';

/**
 * Swiss Ledger is the product's single theme. The palette lives entirely in
 * `index.css` under `[data-theme="ledger"]`; this provider's only job is to
 * stamp that attribute on <html> so the tokens resolve.
 *
 * There is deliberately no theme state, no switcher and no persistence — an
 * earlier multi-theme engine (slate / obsidian) was removed once the product
 * committed to one look, and the no-op provider it left behind was consumed by
 * nothing.
 */
export const LEDGER_THEME = 'ledger' as const;

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', LEDGER_THEME);
  }, []);

  return <>{children}</>;
};

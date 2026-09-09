import { useState } from 'react';

export default function App() {
  const [selectedAppId] = useState<string>('APP-25195');

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
          FinScan AI — Loan Document Reviewer Workspace
        </h1>
        <p style={{ color: '#6b7280', margin: '4px 0 0 0' }}>
          Deterministic code decides. AI explains. A human approves.
        </p>
      </header>

      <main style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Left Column: Dossier Documents & PDF Viewer */}
        <section style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px' }}>Dossier Documents</h2>
          <div style={{ background: '#f3f4f6', height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px' }}>
            <p style={{ color: '#9ca3af' }}>PDF Viewer & Bounding Box Citations (pdf.js)</p>
          </div>
        </section>

        {/* Right Column: Structured Findings & Sign-Off */}
        <section style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px' }}>Audit Findings & Reconciliation</h2>
          <div style={{ background: '#f9fafb', padding: '12px', borderRadius: '4px', marginBottom: '16px' }}>
            <p style={{ margin: 0, fontSize: '14px', color: '#374151' }}>
              <strong>Status:</strong> READY_FOR_REVIEW
            </p>
            <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: '#374151' }}>
              <strong>Application ID:</strong> {selectedAppId}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '24px' }}>
            <button style={{ padding: '8px 16px', background: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Sign Off (Approve)
            </button>
            <button style={{ padding: '8px 16px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Flag Discrepancy (Reject)
            </button>
            <button style={{ padding: '8px 16px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Request Info
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

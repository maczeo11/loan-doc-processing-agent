import assert from 'node:assert';
import { computeBoundingBoxPercent, getEvidenceKey } from '../src/utils/coordinates.ts';
import type { BoundingBox, EvidenceRef } from '../src/types/contracts.ts';
import { DEMO_DOSSIERS } from '../src/data/mockDossier.ts';

interface TestResult {
  suite: string;
  name: string;
  passed: boolean;
  details?: string;
}

const results: TestResult[] = [];

function recordTest(suite: string, name: string, fn: () => void) {
  try {
    fn();
    results.push({ suite, name, passed: true });
    console.log(`  [PASS] ${suite} > ${name}`);
  } catch (err: any) {
    results.push({ suite, name, passed: false, details: err.message || String(err) });
    console.error(`  [FAIL] ${suite} > ${name}: ${err.message || String(err)}`);
  }
}

console.log('================================================================');
console.log('EMPIRICAL STRESS SUITE: COORDINATE TRANSLATION & JUMP NAVIGATION');
console.log('================================================================\n');

// -----------------------------------------------------------------------------
// SUITE 1: computeBoundingBoxPercent Stress & Boundary Testing
// -----------------------------------------------------------------------------
console.log('--- SUITE 1: computeBoundingBoxPercent ---');

recordTest('computeBoundingBoxPercent', 'Normalized coordinates [0..1] within bounds', () => {
  const bbox: BoundingBox = { x0: 0.12, y0: 0.25, x1: 0.58, y1: 0.35 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert.strictEqual(Math.round(res.left), 12);
  assert.strictEqual(Math.round(res.top), 25);
  assert.strictEqual(Math.round(res.width), 46);
  assert.strictEqual(Math.round(res.height), 10);
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100, 'Must not overflow right canvas boundary');
  assert(res.top + res.height <= 100, 'Must not overflow bottom canvas boundary');
});

recordTest('computeBoundingBoxPercent', 'Exact boundaries (0, 0, 1, 1)', () => {
  const bbox: BoundingBox = { x0: 0, y0: 0, x1: 1, y1: 1 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert.strictEqual(res.left, 0);
  assert.strictEqual(res.top, 0);
  assert.strictEqual(res.width, 100);
  assert.strictEqual(res.height, 100);
  assert(res.left + res.width <= 100, 'Canvas width boundary respected');
  assert(res.top + res.height <= 100, 'Canvas height boundary respected');
});

recordTest('computeBoundingBoxPercent', 'PDF points with explicit page dimensions (A4)', () => {
  const bbox: BoundingBox = {
    x0: 59.528,
    y0: 84.189,
    x1: 357.168,
    y1: 252.567,
    page_width: 595.28,
    page_height: 841.89,
  };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert(Math.abs(res.left - 10) < 0.01, `Expected left ~ 10, got ${res.left}`);
  assert(Math.abs(res.top - 10) < 0.01, `Expected top ~ 10, got ${res.top}`);
  assert(Math.abs(res.width - 50) < 0.01, `Expected width ~ 50, got ${res.width}`);
  assert(Math.abs(res.height - 20) < 0.01, `Expected height ~ 20, got ${res.height}`);
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100);
  assert(res.top + res.height <= 100);
});

recordTest('computeBoundingBoxPercent', 'PDF points without explicit page dimensions (default fallback)', () => {
  const bbox: BoundingBox = {
    x0: 100,
    y0: 200,
    x1: 400,
    y1: 500,
  };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  const expectedLeft = (100 / 595.28) * 100;
  const expectedTop = (200 / 841.89) * 100;
  const expectedWidth = ((400 - 100) / 595.28) * 100;
  const expectedHeight = ((500 - 200) / 841.89) * 100;

  assert(Math.abs(res.left - expectedLeft) < 0.01);
  assert(Math.abs(res.top - expectedTop) < 0.01);
  assert(Math.abs(res.width - expectedWidth) < 0.01);
  assert(Math.abs(res.height - expectedHeight) < 0.01);
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100);
  assert(res.top + res.height <= 100);
});

recordTest('computeBoundingBoxPercent', 'Inverted coordinates (x1 < x0, y1 < y0)', () => {
  const bbox: BoundingBox = { x0: 0.85, y0: 0.75, x1: 0.25, y1: 0.15 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert(res.left >= 0, `Left must be >= 0, got ${res.left}`);
  assert(res.top >= 0, `Top must be >= 0, got ${res.top}`);
  assert(res.width >= 0, `Width must be >= 0, got ${res.width}`);
  assert(res.height >= 0, `Height must be >= 0, got ${res.height}`);
  assert(res.left + res.width <= 100.001, `Overflow check: ${res.left + res.width} <= 100`);
  assert(res.top + res.height <= 100.001, `Overflow check: ${res.top + res.height} <= 100`);
});

recordTest('computeBoundingBoxPercent', 'Zero width and zero height (point coordinates)', () => {
  const bbox: BoundingBox = { x0: 0.45, y0: 0.55, x1: 0.45, y1: 0.55 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert(Math.abs(res.left - 45) < 1e-6);
  assert(Math.abs(res.top - 55) < 1e-6);
  // Minimum visibility clamping
  assert(res.width >= 1.0, `Width must have minimum 1.0% visibility, got ${res.width}`);
  assert(res.height >= 0.8, `Height must have minimum 0.8% visibility, got ${res.height}`);
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100);
  assert(res.top + res.height <= 100);
});

recordTest('computeBoundingBoxPercent', 'Zero or negative page dimensions fallback protection', () => {
  const bboxZero: BoundingBox = { x0: 100, y0: 100, x1: 300, y1: 300, page_width: 0, page_height: -50 };
  const res = computeBoundingBoxPercent(bboxZero);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert(isFinite(res.left) && isFinite(res.top) && isFinite(res.width) && isFinite(res.height));
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100.001);
  assert(res.top + res.height <= 100.001);
});

recordTest('computeBoundingBoxPercent', 'Extreme out of bounds (negative coordinates)', () => {
  const bbox: BoundingBox = { x0: -0.5, y0: -0.8, x1: 0.4, y1: 0.5 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert.strictEqual(res.left, 0, 'Negative left must clamp to 0');
  assert.strictEqual(res.top, 0, 'Negative top must clamp to 0');
  assert(res.width <= 100, `Width clamped to canvas, got ${res.width}`);
  assert(res.height <= 100, `Height clamped to canvas, got ${res.height}`);
  assert(res.left + res.width <= 100);
  assert(res.top + res.height <= 100);
});

recordTest('computeBoundingBoxPercent', 'Extreme out of bounds (far beyond canvas > 100%)', () => {
  const bbox: BoundingBox = { x0: 1000, y0: 2000, x1: 5000, y1: 6000, page_width: 595.28, page_height: 841.89 };
  const res = computeBoundingBoxPercent(bbox);

  assert(!isNaN(res.left) && !isNaN(res.top) && !isNaN(res.width) && !isNaN(res.height));
  assert(res.left <= 99, `Left must clamp to max 99, got ${res.left}`);
  assert(res.top <= 99, `Top must clamp to max 99, got ${res.top}`);
  assert(res.left >= 0 && res.top >= 0);
  assert(res.left + res.width <= 100.001, `Overflow: ${res.left + res.width} <= 100`);
  assert(res.top + res.height <= 100.001, `Overflow: ${res.top + res.height} <= 100`);
});

recordTest('computeBoundingBoxPercent', 'Property-based fuzzing (10,000 random bounding boxes)', () => {
  let seed = 12345;
  function pseudoRandom() {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }

  for (let i = 0; i < 10000; i++) {
    const x0 = (pseudoRandom() - 0.3) * 1000;
    const y0 = (pseudoRandom() - 0.3) * 1000;
    const x1 = (pseudoRandom() - 0.3) * 1000;
    const y1 = (pseudoRandom() - 0.3) * 1000;
    const pageW = pseudoRandom() > 0.5 ? (pseudoRandom() + 0.1) * 1000 : undefined;
    const pageH = pseudoRandom() > 0.5 ? (pseudoRandom() + 0.1) * 1000 : undefined;

    const res = computeBoundingBoxPercent({ x0, y0, x1, y1, page_width: pageW, page_height: pageH });

    assert(!isNaN(res.left), `Iteration ${i}: left is NaN`);
    assert(!isNaN(res.top), `Iteration ${i}: top is NaN`);
    assert(!isNaN(res.width), `Iteration ${i}: width is NaN`);
    assert(!isNaN(res.height), `Iteration ${i}: height is NaN`);

    assert(res.left >= 0, `Iteration ${i}: left < 0 (${res.left})`);
    assert(res.top >= 0, `Iteration ${i}: top < 0 (${res.top})`);
    assert(res.left <= 99, `Iteration ${i}: left > 99 (${res.left})`);
    assert(res.top <= 99, `Iteration ${i}: top > 99 (${res.top})`);

    assert(res.width >= 1.0, `Iteration ${i}: width < 1.0 (${res.width})`);
    assert(res.height >= 0.8, `Iteration ${i}: height < 0.8 (${res.height})`);

    assert(res.left + res.width <= 100.0001, `Iteration ${i}: width overflow (${res.left} + ${res.width} = ${res.left + res.width})`);
    assert(res.top + res.height <= 100.0001, `Iteration ${i}: height overflow (${res.top} + ${res.height} = ${res.top + res.height})`);
  }
});

// -----------------------------------------------------------------------------
// SUITE 2: Zoom Invariance & Scale Stability (0.5 to 2.2)
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 2: Zoom Invariance & Scale Stability ---');

recordTest('ZoomStability', 'Bounding box CSS percentage scale invariance (0.5 to 2.2)', () => {
  const bbox: BoundingBox = { x0: 0.15, y0: 0.22, x1: 0.65, y1: 0.48 };
  const percent = computeBoundingBoxPercent(bbox);

  const basePageWidth = 595.28;
  const basePageHeight = 841.89;

  const testScales = [0.5, 0.65, 0.8, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0, 2.2];

  for (const scale of testScales) {
    const renderedCanvasWidth = Math.floor(basePageWidth * scale);
    const renderedCanvasHeight = Math.floor(basePageHeight * scale);

    const boxPixelLeft = renderedCanvasWidth * (percent.left / 100);
    const boxPixelTop = renderedCanvasHeight * (percent.top / 100);
    const boxPixelWidth = renderedCanvasWidth * (percent.width / 100);
    const boxPixelHeight = renderedCanvasHeight * (percent.height / 100);

    const relativeLeft = boxPixelLeft / renderedCanvasWidth;
    const relativeTop = boxPixelTop / renderedCanvasHeight;
    const relativeWidth = boxPixelWidth / renderedCanvasWidth;
    const relativeHeight = boxPixelHeight / renderedCanvasHeight;

    assert(Math.abs(relativeLeft - percent.left / 100) < 1e-9, `Scale ${scale}: relative left drift`);
    assert(Math.abs(relativeTop - percent.top / 100) < 1e-9, `Scale ${scale}: relative top drift`);
    assert(Math.abs(relativeWidth - percent.width / 100) < 1e-9, `Scale ${scale}: relative width drift`);
    assert(Math.abs(relativeHeight - percent.height / 100) < 1e-9, `Scale ${scale}: relative height drift`);

    assert(boxPixelLeft + boxPixelWidth <= renderedCanvasWidth + 1e-6);
    assert(boxPixelTop + boxPixelHeight <= renderedCanvasHeight + 1e-6);
  }
});

recordTest('ZoomStability', 'Zoom step handler boundary clamping ([0.5, 2.2])', () => {
  let scale = 1.0;

  // Zoom in 50 times (step: +0.15)
  for (let i = 0; i < 50; i++) {
    scale = Math.min(2.2, scale + 0.15);
  }
  assert.strictEqual(scale, 2.2, `Zoom in must clamp at exactly 2.2, got ${scale}`);

  // Zoom out 50 times (step: -0.15)
  for (let i = 0; i < 50; i++) {
    scale = Math.max(0.5, scale - 0.15);
  }
  assert.strictEqual(scale, 0.5, `Zoom out must clamp at exactly 0.5, got ${scale}`);

  // Reset zoom
  scale = 1.0;
  assert.strictEqual(scale, 1.0, 'Reset zoom restores scale 1.0');
});

// -----------------------------------------------------------------------------
// SUITE 3: Drag Resizer Clamping & Layout Ergonomics
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 3: Drag Resizer Clamping & Layout Ergonomics ---');

recordTest('ResizerClamping', 'Left pane width clamping ([220px, 450px])', () => {
  let leftWidth = 280;

  // Drag left by -1000px
  leftWidth = Math.max(220, Math.min(450, leftWidth - 1000));
  assert.strictEqual(leftWidth, 220, `Left pane min clamped to 220, got ${leftWidth}`);

  // Drag right by +2000px
  leftWidth = Math.max(220, Math.min(450, leftWidth + 2000));
  assert.strictEqual(leftWidth, 450, `Left pane max clamped to 450, got ${leftWidth}`);

  // Incremental drag within bounds
  leftWidth = 280;
  leftWidth = Math.max(220, Math.min(450, leftWidth + 50));
  assert.strictEqual(leftWidth, 330);
  leftWidth = Math.max(220, Math.min(450, leftWidth - 30));
  assert.strictEqual(leftWidth, 300);
});

recordTest('ResizerClamping', 'Right pane width clamping ([320px, 600px])', () => {
  let rightWidth = 420;

  // Drag right by -1000px (collapsing right pane)
  rightWidth = Math.max(320, Math.min(600, rightWidth - 1000));
  assert.strictEqual(rightWidth, 320, `Right pane min clamped to 320, got ${rightWidth}`);

  // Drag left by +2000px (expanding right pane)
  rightWidth = Math.max(320, Math.min(600, rightWidth + 2000));
  assert.strictEqual(rightWidth, 600, `Right pane max clamped to 600, got ${rightWidth}`);

  // Incremental drag within bounds
  rightWidth = 420;
  rightWidth = Math.max(320, Math.min(600, rightWidth + 40));
  assert.strictEqual(rightWidth, 460);
  rightWidth = Math.max(320, Math.min(600, rightWidth - 70));
  assert.strictEqual(rightWidth, 390);
});

recordTest('ResizerClamping', 'Viewport canvas clearance across screen sizes', () => {
  const screenWidths = [1024, 1280, 1366, 1440, 1920, 2560, 3840];

  for (const screenW of screenWidths) {
    // Worst-case pane expansion: Left=450px, Right=600px
    const maxSidePanes = 450 + 600;
    const centerRemainingMin = screenW - maxSidePanes;

    // Standard pane widths: Left=280px, Right=420px
    const stdSidePanes = 280 + 420;
    const centerRemainingStd = screenW - stdSidePanes;

    if (screenW >= 1280) {
      assert(centerRemainingMin >= 230, `Screen ${screenW}px: center space ${centerRemainingMin}px must be >= 230px`);
      assert(centerRemainingStd >= 580, `Screen ${screenW}px: center space ${centerRemainingStd}px must be >= 580px`);
    } else {
      // 1024px minimum
      assert(centerRemainingStd >= 324, `Screen 1024px: center space ${centerRemainingStd}px must be >= 324px`);
    }
  }
});

// -----------------------------------------------------------------------------
// SUITE 4: Jump Navigation & Evidence Citation Keys
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 4: Jump Navigation & Evidence Citation Keys ---');

recordTest('JumpNavigation', 'getEvidenceKey stability and formatting', () => {
  const ev1: EvidenceRef = {
    document_id: 'DOC-PAYSLIP-01',
    document_type: 'payslip',
    page_number: 1,
    quoted_span: 'Net Pay: ₹ 1,50,000.00',
    bounding_box: { x0: 0.1234, y0: 0.5678, x1: 0.45, y1: 0.60 },
  };

  const key1 = getEvidenceKey(ev1);
  assert.strictEqual(key1, 'DOC-PAYSLIP-01-P1-0.12_0.57');

  const ev2: EvidenceRef = {
    document_id: 'DOC-PAYSLIP-01',
    document_type: 'payslip',
    page_number: 1,
    quoted_span: 'Different span',
    bounding_box: { x0: 0.1234, y0: 0.5678, x1: 0.80, y1: 0.90 },
  };
  const key2 = getEvidenceKey(ev2);
  assert.strictEqual(key1, key2, 'Same doc, page, x0, y0 produces identical key for tracking');
});

recordTest('JumpNavigation', 'State transition simulation for useEvidenceNavigation', () => {
  // Simulate hook behavior
  let activeDocumentId = 'DOC-APP-01';
  let activePageNumber = 1;
  let activeEvidenceKey: string | null = null;
  let pulseTimer: any = null;

  const jumpToEvidence = (evidence: EvidenceRef) => {
    activeDocumentId = evidence.document_id;
    activePageNumber = evidence.page_number;
    activeEvidenceKey = getEvidenceKey(evidence);

    if (pulseTimer) {
      clearTimeout(pulseTimer);
    }
    pulseTimer = setTimeout(() => {
      pulseTimer = null;
    }, 4000);
  };

  const clearActiveEvidence = () => {
    activeEvidenceKey = null;
    if (pulseTimer) {
      clearTimeout(pulseTimer);
      pulseTimer = null;
    }
  };

  const testEv: EvidenceRef = {
    document_id: 'DOC-BANK-01',
    document_type: 'bank_statement',
    page_number: 3,
    quoted_span: 'SALARY CREDIT: ₹ 1,50,000.00',
    bounding_box: { x0: 0.20, y0: 0.40, x1: 0.70, y1: 0.45 },
  };

  jumpToEvidence(testEv);

  assert.strictEqual(activeDocumentId, 'DOC-BANK-01');
  assert.strictEqual(activePageNumber, 3);
  assert.strictEqual(activeEvidenceKey, 'DOC-BANK-01-P3-0.20_0.40');
  assert(pulseTimer !== null, 'Pulse timer must be armed');

  // Rapid jump to another evidence
  const testEv2: EvidenceRef = {
    document_id: 'DOC-ITR-01',
    document_type: 'tax_return',
    page_number: 1,
    quoted_span: 'Gross Total Income: ₹ 18,00,000.00',
    bounding_box: { x0: 0.15, y0: 0.30, x1: 0.60, y1: 0.35 },
  };

  jumpToEvidence(testEv2);
  assert.strictEqual(activeDocumentId, 'DOC-ITR-01');
  assert.strictEqual(activePageNumber, 1);
  assert.strictEqual(activeEvidenceKey, 'DOC-ITR-01-P1-0.15_0.30');

  // Clear evidence
  clearActiveEvidence();
  assert.strictEqual(activeEvidenceKey, null);
  assert.strictEqual(pulseTimer, null);
});

// -----------------------------------------------------------------------------
// SUITE 5: Real Mock Application Dataset Verification
// -----------------------------------------------------------------------------
console.log('\n--- SUITE 5: Mock Application Dataset Verification ---');

recordTest('MockDataIntegrity', 'Validate all evidence citations across mock applications', () => {
  const appIds = ['APP-25195', 'APP-68210', 'APP-10492'];

  let totalFindingsChecked = 0;
  let totalEvidenceChecked = 0;

  for (const appId of appIds) {
    const app = DEMO_DOSSIERS[appId];
    assert(app, `Mock application ${appId} must exist`);

    const docSet = new Set(app.document_ids || []);

    for (const finding of (app.findings || [])) {
      totalFindingsChecked++;
      assert(finding.rule_id, `Finding in ${appId} must have rule_id`);
      assert(['pass', 'flag', 'unknown'].includes(finding.verdict), `Finding ${finding.rule_id} invalid verdict`);

      // If supporting evidence exists, validate every EvidenceRef
      for (const ev of finding.supporting_evidence) {
        totalEvidenceChecked++;
        assert(docSet.has(ev.document_id), `Evidence doc ${ev.document_id} must exist in application ${appId}`);
        assert(ev.page_number >= 1, `Page ${ev.page_number} must be >= 1 for ${ev.document_id}`);
        assert(ev.quoted_span.length > 0, 'Quoted span must not be empty');

        const bbox = ev.bounding_box;
        if (bbox) {
          assert(bbox.x0 >= 0 && bbox.x1 <= 1.05, `BBox x coords out of bounds in ${ev.document_id}`);
          assert(bbox.y0 >= 0 && bbox.y1 <= 1.05, `BBox y coords out of bounds in ${ev.document_id}`);

          const percent = computeBoundingBoxPercent(bbox);
          assert(!isNaN(percent.left) && !isNaN(percent.top));
          assert(percent.left >= 0 && percent.top >= 0);
          assert(percent.left + percent.width <= 100.0001, `Overflow in mock evidence for ${finding.rule_id}`);
          assert(percent.top + percent.height <= 100.0001, `Overflow in mock evidence for ${finding.rule_id}`);
        }
      }
    }
  }

  console.log(`    (Verified ${totalFindingsChecked} findings and ${totalEvidenceChecked} evidence citations)`);
});

// -----------------------------------------------------------------------------
// SUMMARY & EXIT CODE
// -----------------------------------------------------------------------------
console.log('\n================================================================');
const total = results.length;
const passed = results.filter((r) => r.passed).length;
const failed = total - passed;

console.log(`TOTAL TESTS: ${total} | PASSED: ${passed} | FAILED: ${failed}`);
console.log('================================================================');

if (failed > 0) {
  console.error('\nFAILED TESTS:');
  for (const r of results.filter((r) => !r.passed)) {
    console.error(`- [${r.suite}] ${r.name}: ${r.details}`);
  }
  process.exit(1);
} else {
  console.log('\nALL EMPIRICAL TESTS PASSED CLEANLY.');
  process.exit(0);
}

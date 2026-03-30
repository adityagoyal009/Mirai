import { useState, useEffect, useRef } from 'react';
import type { DialogState } from '../game/dialog/DialogManager';

/* ------------------------------------------------------------------ */
/*  InteractPrompt — "Press E - Talk to [npcName]"                    */
/* ------------------------------------------------------------------ */

export function InteractPrompt({ npcName, visible }: { npcName: string; visible: boolean }) {
  return (
    <div
      style={{
        ...styles.promptPill,
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(6px)',
      }}
    >
      <span style={styles.promptKey}>E</span>
      <span style={styles.promptLabel}>Talk to {npcName}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  DialogBox — full dialog interaction UI                            */
/* ------------------------------------------------------------------ */

export function DialogBox({
  dialogState,
  onAdvance,
  onCancel,
}: {
  dialogState: DialogState;
  onAdvance: (response?: string) => void;
  onCancel: () => void;
}) {
  const [inputValue, setInputValue] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [showTextFallback, setShowTextFallback] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // When step changes, clear state
  useEffect(() => {
    setInputValue('');
    setUploadError('');
    setShowTextFallback(false);
    setUploading(false);
    if (inputRef.current) inputRef.current.focus();
  }, [dialogState.stepIndex]);

  // Global keyboard listener for Enter (continue) and Escape (cancel)
  useEffect(() => {
    if (!dialogState.active) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onCancel();
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        const step = dialogState.currentStep;
        if (!step) return;

        // For non-input steps, Enter = continue
        if (!step.expectsInput) {
          e.preventDefault();
          e.stopPropagation();
          onAdvance();
        }
        // For text steps with a value, Enter = submit (unless in textarea with shift)
        // This is handled by the textarea's own onKeyDown, so skip here
      }
    };

    window.addEventListener('keydown', handler, true); // capture phase to beat Phaser
    return () => window.removeEventListener('keydown', handler, true);
  }, [dialogState.active, dialogState.currentStep, onAdvance, onCancel]);

  if (!dialogState.active || !dialogState.currentStep) return null;

  const step = dialogState.currentStep;

  const handleSubmit = () => {
    if (step.expectsInput) {
      if (!inputValue.trim()) return;
      onAdvance(inputValue.trim());
    } else {
      onAdvance();
    }
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && step.inputType !== 'file') {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape') {
      onCancel();
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF files are accepted.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('File too large. Maximum 5MB.');
      return;
    }

    setUploading(true);
    setUploadError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiBase = window.location.port === '5000' || window.location.pathname.startsWith('/game')
        ? '' : 'http://localhost:5000';
      const resp = await fetch(`${apiBase}/api/bi/extract-pdf`, {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();

      if (!data.success) {
        setUploadError(data.error || 'Extraction failed.');
        setUploading(false);
        return;
      }

      // Use standardized text if available, else raw text
      const extractedText = data.standardized || data.raw_text || '';
      if (!extractedText.trim()) {
        setUploadError('Could not extract text from this PDF.');
        setUploading(false);
        return;
      }

      // Advance dialog with extracted text as the exec summary
      setUploading(false);
      onAdvance(extractedText);
    } catch (err) {
      setUploadError('Failed to connect to backend. Is the server running?');
      setUploading(false);
    }
  };

  const isFileStep = step.expectsInput && step.inputType === 'file';

  return (
    <div style={styles.dialogContainer}>
      <div style={styles.dialogBox}>
        <div style={styles.npcName}>{dialogState.npcName}</div>

        {step.text && <div style={styles.dialogText}>{step.text}</div>}

        {/* File upload + text fallback input */}
        {isFileStep && !showTextFallback && (
          <div>
            <div style={styles.fileUploadArea}>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileUpload(f);
                }}
              />
              <button
                onClick={() => fileRef.current?.click()}
                style={styles.uploadBtn}
                disabled={uploading}
              >
                {uploading ? 'Extracting with Opus 4.6...' : 'Upload PDF (max 4 pages)'}
              </button>
              <button
                onClick={() => setShowTextFallback(true)}
                style={styles.textFallbackBtn}
              >
                or paste text instead
              </button>
            </div>
            {uploading && (
              <div style={styles.uploadProgress}>
                Analyzing your document with vision AI...
              </div>
            )}
            {uploadError && (
              <div style={styles.uploadError}>{uploadError}</div>
            )}
          </div>
        )}

        {/* Text fallback for file step */}
        {isFileStep && showTextFallback && (
          <div>
            <textarea
              ref={inputRef as React.RefObject<HTMLTextAreaElement>}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste your executive summary here..."
              style={styles.textarea}
              rows={4}
            />
            <button
              onClick={() => setShowTextFallback(false)}
              style={{ ...styles.textFallbackBtn, marginTop: 4 }}
            >
              or upload PDF instead
            </button>
          </div>
        )}

        {/* Regular text input (non-file steps) */}
        {step.expectsInput && step.inputType === 'text' && (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response..."
            style={styles.textarea}
            rows={3}
          />
        )}

        {/* Select input */}
        {step.expectsInput && step.inputType === 'select' && (
          <select
            ref={inputRef as React.RefObject<HTMLSelectElement>}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            style={styles.select}
          >
            <option value="">-- Select --</option>
            {step.inputOptions?.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )}

        {/* Action buttons */}
        <div style={styles.actions}>
          {step.expectsInput && !isFileStep ? (
            <button onClick={handleSubmit} style={styles.btnPrimary} disabled={!inputValue.trim()}>
              SUBMIT
            </button>
          ) : isFileStep && showTextFallback ? (
            <button onClick={handleSubmit} style={styles.btnPrimary} disabled={!inputValue.trim()}>
              SUBMIT TEXT
            </button>
          ) : !step.expectsInput ? (
            <button onClick={() => onAdvance()} style={styles.btnPrimary}>
              CONTINUE
            </button>
          ) : null}
          <button onClick={onCancel} style={styles.btnCancel}>ESC</button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                            */
/* ------------------------------------------------------------------ */

const styles: Record<string, React.CSSProperties> = {
  /* InteractPrompt */
  promptPill: {
    position: 'absolute',
    bottom: 48,
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: 'rgba(10,10,15,0.85)',
    padding: '6px 16px',
    borderRadius: 6,
    border: '1px solid #333',
    pointerEvents: 'auto',
    transition: 'opacity 0.2s ease, transform 0.2s ease',
    whiteSpace: 'nowrap',
  },
  promptKey: {
    fontFamily: "'Courier New', monospace",
    fontSize: 11,
    fontWeight: 'bold',
    color: '#4a9eff',
    background: '#1a2744',
    border: '1px solid #4a9eff44',
    borderRadius: 3,
    padding: '1px 7px',
    letterSpacing: 1,
  },
  promptLabel: {
    fontFamily: "'Courier New', monospace",
    fontSize: 11,
    color: '#888',
    letterSpacing: 1,
  },

  /* DialogBox */
  dialogContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    pointerEvents: 'auto',
    zIndex: 20,
  },
  dialogBox: {
    background: 'rgba(10,10,20,0.95)',
    borderTop: '1px solid #4a9eff44',
    padding: '12px 20px 14px',
    maxHeight: 200,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  npcName: {
    fontFamily: "'Courier New', monospace",
    fontSize: 11,
    fontWeight: 'bold',
    color: '#4a9eff',
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  dialogText: {
    fontFamily: "'Courier New', monospace",
    fontSize: 12,
    color: '#ddd',
    lineHeight: '1.5',
  },
  textarea: {
    fontFamily: "'Courier New', monospace",
    fontSize: 12,
    color: '#ddd',
    background: '#0e0e18',
    border: '1px solid #333',
    borderRadius: 3,
    padding: '6px 10px',
    resize: 'vertical' as const,
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  },
  select: {
    fontFamily: "'Courier New', monospace",
    fontSize: 12,
    color: '#ddd',
    background: '#0e0e18',
    border: '1px solid #333',
    borderRadius: 3,
    padding: '6px 10px',
    outline: 'none',
    cursor: 'pointer',
    width: '100%',
    boxSizing: 'border-box',
  },
  actions: {
    display: 'flex',
    gap: 8,
    marginTop: 2,
  },
  btnPrimary: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#4a9eff',
    background: '#1a2744',
    border: '1px solid #4a9eff44',
    padding: '4px 12px',
    borderRadius: 3,
    cursor: 'pointer',
    letterSpacing: 1,
  },
  btnCancel: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#888',
    background: '#1a1a22',
    border: '1px solid #333',
    padding: '4px 12px',
    borderRadius: 3,
    cursor: 'pointer',
    letterSpacing: 1,
  },

  /* File upload */
  fileUploadArea: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  uploadBtn: {
    fontFamily: "'Courier New', monospace",
    fontSize: 11,
    color: '#4a9eff',
    background: '#1a2744',
    border: '1px dashed #4a9eff66',
    padding: '8px 20px',
    borderRadius: 4,
    cursor: 'pointer',
    letterSpacing: 1,
  },
  textFallbackBtn: {
    fontFamily: "'Courier New', monospace",
    fontSize: 9,
    color: '#666',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    textDecoration: 'underline',
    padding: 0,
  },
  uploadProgress: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#4a9eff',
    marginTop: 6,
    letterSpacing: 1,
  },
  uploadError: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#ff6666',
    marginTop: 6,
  },
};

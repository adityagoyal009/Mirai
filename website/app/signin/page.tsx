"use client";

import { useSession, signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";

const ERROR_MESSAGES: Record<string, string> = {
  OAuthAccountNotLinked: "This email is already associated with another sign-in method.",
  AccessDenied: "Google sign-in was cancelled before completion.",
  default: "Something went wrong during sign-in. Please try again.",
};

export default function SignInPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-white/50">Loading...</div>}>
      <SignInContent />
    </Suspense>
  );
}

function SignInContent() {
  const { data: session } = useSession();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";
  const errorCode = searchParams.get("error");
  const [googleConfigured, setGoogleConfigured] = useState(true);

  useEffect(() => {
    fetch("/api/auth/session")
      .then((r) => r.json())
      .then((d) => setGoogleConfigured(d.google_oauth_configured ?? true))
      .catch(() => {});
  }, []);

  const user = session?.user;
  const errorMessage = errorCode
    ? ERROR_MESSAGES[errorCode] || ERROR_MESSAGES.default
    : null;

  return (
    <div className="signin-shell">
      <style>{`
        .signin-shell {
          min-height: 100vh;
          display: grid;
          grid-template-columns: 1fr;
          position: relative;
          overflow: hidden;
          background:
            radial-gradient(circle at 14% 18%, rgba(155, 213, 255, 0.16), transparent 24%),
            radial-gradient(circle at 84% 24%, rgba(52, 199, 160, 0.14), transparent 18%),
            radial-gradient(circle at 50% 80%, rgba(255, 131, 87, 0.08), transparent 20%),
            linear-gradient(135deg, #08182c 0%, #0f2440 42%, #17355f 100%);
          color: #fff;
          font-family: "DM Sans", system-ui, sans-serif;
        }

        @media (min-width: 900px) {
          .signin-shell {
            grid-template-columns: 1.1fr 0.9fr;
          }
        }

        .signin-shell::before {
          content: "";
          position: absolute;
          top: -120px;
          right: -100px;
          width: 500px;
          height: 500px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(155, 213, 255, 0.18) 0%, transparent 65%);
          pointer-events: none;
        }

        .signin-shell::after {
          content: "";
          position: absolute;
          bottom: -180px;
          left: -100px;
          width: 600px;
          height: 600px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(243, 177, 63, 0.08) 0%, transparent 60%);
          pointer-events: none;
        }

        .signin-left {
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 60px 48px;
          position: relative;
          z-index: 1;
        }

        @media (max-width: 899px) {
          .signin-left {
            padding: 40px 24px 20px;
            text-align: center;
            align-items: center;
          }
        }

        .signin-eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          font-size: 0.82rem;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          font-weight: 700;
          color: rgba(255, 255, 255, 0.6);
        }

        .signin-eyebrow::before {
          content: "";
          width: 30px;
          height: 1px;
          background: linear-gradient(90deg, rgba(255,255,255,0.15), rgba(52,199,160,0.7));
        }

        .signin-title {
          margin-top: 24px;
          font-family: "Instrument Serif", Georgia, serif;
          font-size: clamp(3rem, 7vw, 5.4rem);
          line-height: 0.9;
          letter-spacing: -0.04em;
          text-shadow: 0 12px 30px rgba(0,0,0,0.25);
        }

        .signin-title span {
          font-style: italic;
          color: #9bd5ff;
        }

        .signin-lead {
          margin-top: 22px;
          max-width: 480px;
          font-size: 1.08rem;
          line-height: 1.6;
          color: rgba(255, 255, 255, 0.68);
        }

        .signin-features {
          margin-top: 36px;
          display: grid;
          gap: 16px;
        }

        .signin-feature {
          display: flex;
          align-items: flex-start;
          gap: 14px;
          padding: 16px 18px;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.07);
          backdrop-filter: blur(10px);
        }

        .signin-feature-icon {
          width: 38px;
          height: 38px;
          border-radius: 12px;
          display: grid;
          place-items: center;
          flex-shrink: 0;
          font-size: 0.85rem;
          font-weight: 800;
          color: #0f2440;
          background: linear-gradient(135deg, #d6e9ff, #fff1dd);
        }

        .signin-feature strong {
          display: block;
          font-size: 0.92rem;
          margin-bottom: 3px;
        }

        .signin-feature p {
          color: rgba(255, 255, 255, 0.6);
          font-size: 0.86rem;
          line-height: 1.45;
        }

        .signin-stats {
          display: flex;
          gap: 28px;
          margin-top: 36px;
          padding-top: 28px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .signin-stat strong {
          display: block;
          font-family: "Instrument Serif", Georgia, serif;
          font-size: 1.8rem;
          letter-spacing: -0.03em;
          line-height: 1;
        }

        .signin-stat span {
          display: block;
          margin-top: 5px;
          color: rgba(255, 255, 255, 0.5);
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          font-weight: 700;
        }

        .signin-right {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 40px 32px;
          position: relative;
          z-index: 1;
        }

        @media (max-width: 899px) {
          .signin-right {
            padding: 20px 24px 60px;
          }
        }

        .signin-card {
          width: 100%;
          max-width: 420px;
          padding: 36px 32px;
          border-radius: 32px;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.06)),
            rgba(9, 24, 44, 0.55);
          border: 1px solid rgba(255, 255, 255, 0.1);
          box-shadow: 0 40px 100px rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(20px);
        }

        .signin-card-brand {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 28px;
        }

        .signin-card-mark {
          width: 44px;
          height: 44px;
          border-radius: 14px;
          display: grid;
          place-items: center;
          font-size: 1.15rem;
          font-weight: 700;
          color: #0f2440;
          background: linear-gradient(135deg, #d6e9ff, #fff1dd);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
        }

        .signin-card-title {
          text-align: center;
          font-size: 1.5rem;
          font-weight: 800;
          letter-spacing: -0.02em;
        }

        .signin-card-sub {
          text-align: center;
          margin-top: 8px;
          color: rgba(255, 255, 255, 0.6);
          font-size: 0.92rem;
        }

        .signin-google-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          width: 100%;
          min-height: 56px;
          margin-top: 24px;
          padding: 0 24px;
          border-radius: 999px;
          border: none;
          font-size: 1rem;
          font-weight: 700;
          cursor: pointer;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          color: #1a1a1a;
          background: linear-gradient(135deg, #ffffff, #f0f0f0);
          box-shadow: 0 16px 40px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.9);
        }

        .signin-google-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255,255,255,0.9);
        }

        .signin-google-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }

        .signin-google-icon {
          width: 20px;
          height: 20px;
        }

        .signin-divider {
          display: flex;
          align-items: center;
          gap: 14px;
          margin: 24px 0;
          color: rgba(255, 255, 255, 0.3);
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
        }

        .signin-divider::before,
        .signin-divider::after {
          content: "";
          flex: 1;
          height: 1px;
          background: rgba(255, 255, 255, 0.1);
        }

        .signin-bullets {
          list-style: none;
          padding: 0;
          margin: 0;
          display: grid;
          gap: 10px;
        }

        .signin-bullets li {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.88rem;
          color: rgba(255, 255, 255, 0.7);
        }

        .signin-bullets li::before {
          content: "";
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: linear-gradient(135deg, #9bd5ff, #34c7a0);
          flex-shrink: 0;
        }

        .signin-error {
          margin-top: 16px;
          padding: 14px 16px;
          border-radius: 18px;
          background: rgba(255, 131, 87, 0.15);
          border: 1px solid rgba(255, 131, 87, 0.25);
          color: #ffcfbb;
          font-size: 0.9rem;
        }

        .signin-nav-links {
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-top: 20px;
        }

        .signin-nav-link {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 48px;
          padding: 0 20px;
          border-radius: 999px;
          font-weight: 700;
          font-size: 0.92rem;
          transition: all 0.2s ease;
          text-decoration: none;
          color: #fff;
        }

        .signin-nav-primary {
          background: linear-gradient(135deg, #196cff, #4b95ff);
          box-shadow: 0 14px 32px rgba(25, 108, 255, 0.25);
        }

        .signin-nav-primary:hover {
          transform: translateY(-2px);
        }

        .signin-nav-ghost {
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(255, 255, 255, 0.05);
        }

        .signin-nav-ghost:hover {
          background: rgba(255, 255, 255, 0.1);
        }

        .signin-session-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          margin-bottom: 20px;
          padding: 12px 16px;
          border-radius: 18px;
          background: rgba(52, 199, 160, 0.12);
          border: 1px solid rgba(52, 199, 160, 0.2);
        }

        .signin-session-badge::before {
          content: "";
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #34c7a0;
          box-shadow: 0 0 0 4px rgba(52, 199, 160, 0.15);
        }

        .signin-home-link {
          display: block;
          text-align: center;
          margin-top: 20px;
          color: rgba(255, 255, 255, 0.4);
          font-size: 0.86rem;
          text-decoration: none;
          transition: color 0.2s ease;
        }

        .signin-home-link:hover {
          color: rgba(255, 255, 255, 0.7);
        }
      `}</style>

      {/* Left — Hero Content */}
      <div className="signin-left">
        <div className="signin-eyebrow">Mirai due diligence engine</div>
        <h1 className="signin-title">
          One sign-in.<br />
          <span>Full conviction.</span>
        </h1>
        <p className="signin-lead">
          Submit a startup once. Receive a research-backed decision memo with
          multi-model scoring, persona swarm analysis, and scenario simulation.
        </p>

        <div className="signin-features">
          <div className="signin-feature">
            <div className="signin-feature-icon">1</div>
            <div>
              <strong>Submit the brief</strong>
              <p>Company name, pitch, market, traction, and risk. One clean form.</p>
            </div>
          </div>
          <div className="signin-feature">
            <div className="signin-feature-icon">2</div>
            <div>
              <strong>Mirai evaluates</strong>
              <p>10-model council scores independently. Persona swarm pressure-tests the thesis.</p>
            </div>
          </div>
          <div className="signin-feature">
            <div className="signin-feature-icon">3</div>
            <div>
              <strong>Download the memo</strong>
              <p>PitchBook-quality report with scoring, tensions, and strategic next moves.</p>
            </div>
          </div>
        </div>

        <div className="signin-stats">
          <div className="signin-stat">
            <strong style={{ color: "#9bd5ff" }}>10</strong>
            <span>Model Council</span>
          </div>
          <div className="signin-stat">
            <strong style={{ color: "#34c7a0" }}>1.6M+</strong>
            <span>Personas</span>
          </div>
          <div className="signin-stat">
            <strong style={{ color: "#f3b13f" }}>5</strong>
            <span>Phase Pipeline</span>
          </div>
        </div>
      </div>

      {/* Right — Auth Card */}
      <div className="signin-right">
        <div className="signin-card">
          <div className="signin-card-brand">
            <div className="signin-card-mark">未来</div>
          </div>

          {user ? (
            <>
              <div className="signin-session-badge">
                <strong style={{ fontSize: "0.9rem" }}>{user.name || user.email}</strong>
              </div>
              <h2 className="signin-card-title">Welcome back</h2>
              <p className="signin-card-sub">Your session is active. Where to?</p>
              <div className="signin-nav-links">
                <Link href="/dashboard" className="signin-nav-link signin-nav-primary">
                  Go to Dashboard
                </Link>
                <Link href="/submit" className="signin-nav-link signin-nav-ghost">
                  Submit a Company
                </Link>
                {user.isAdmin && (
                  <Link href="/admin" className="signin-nav-link signin-nav-ghost">
                    Admin Board
                  </Link>
                )}
              </div>
            </>
          ) : (
            <>
              <h2 className="signin-card-title">Sign in</h2>
              <p className="signin-card-sub">
                Authenticate to submit companies and access your reports.
              </p>

              {errorMessage && (
                <div className="signin-error">{errorMessage}</div>
              )}

              {googleConfigured ? (
                <button
                  onClick={() => signIn("google", { callbackUrl })}
                  className="signin-google-btn"
                >
                  <svg className="signin-google-icon" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 001 12c0 1.77.42 3.44 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Continue with Google
                </button>
              ) : (
                <button disabled className="signin-google-btn" style={{ opacity: 0.4 }}>
                  Google OAuth Not Configured
                </button>
              )}

              <div className="signin-divider">after sign-in</div>

              <ul className="signin-bullets">
                <li>Submit startups for multi-model evaluation</li>
                <li>Track queue status in real time</li>
                <li>Download completed decision memos</li>
                <li>View scores, swarm analysis, and simulations</li>
              </ul>
            </>
          )}

          <Link href="/" className="signin-home-link">
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}

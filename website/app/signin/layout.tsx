export default function SignInLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, overflow: "auto" }}>
      {children}
    </div>
  );
}

import type { Metadata } from "next";
import { DM_Sans, Instrument_Serif } from "next/font/google";
import Providers from "@/components/providers";
import Navbar from "@/components/navbar";
import Footer from "@/components/footer";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "700", "800"],
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  variable: "--font-display",
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: {
    default: "Mirai | AI Startup Due Diligence",
    template: "%s | Mirai",
  },
  description:
    "Research-backed startup diligence with live web research, model debate, swarm reaction, and structured decision memos.",
  metadataBase: new URL(process.env.NEXTAUTH_URL || "http://localhost:3000"),
  openGraph: {
    title: "Mirai | AI Startup Due Diligence That Shows Its Work",
    description:
      "Multi-model council scoring, persona swarm reaction, and scenario simulation for startup evaluation.",
    type: "website",
  },
};

export const viewport = {
  themeColor: "#0f2440",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang={`en`} className={`${dmSans.variable} ${instrumentSerif.variable}`}>
      <body className="font-body text-ink antialiased min-h-screen bg-paper">
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}

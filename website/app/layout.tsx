import type { Metadata } from "next";
import { DM_Sans, Instrument_Serif } from "next/font/google";
import Providers from "@/components/providers";
import Navbar from "@/components/navbar";
import Footer from "@/components/footer";
import Analytics from "@/components/analytics";
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
    default: "Mirai by VC Labs | AI Startup Due Diligence",
    template: "%s | Mirai by VC Labs",
  },
  description:
    "Research-backed startup diligence with live web research, multi-model council debate, swarm reaction, scenario simulation, and structured decision memos. Built by VC Labs.",
  metadataBase: new URL("https://vclabs.org"),
  keywords: [
    "startup due diligence",
    "AI startup evaluation",
    "venture capital AI",
    "startup analysis tool",
    "VC due diligence",
    "startup scoring",
    "AI investment memo",
    "startup risk assessment",
    "multi-model AI council",
    "swarm intelligence startups",
    "VC Labs",
    "Mirai",
  ],
  authors: [{ name: "VC Labs", url: "https://vclabs.org" }],
  creator: "VC Labs",
  publisher: "VC Labs",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    title: "Mirai | AI Startup Due Diligence That Shows Its Work",
    description:
      "Multi-model council scoring, persona swarm reaction, and scenario simulation for startup evaluation. By VC Labs.",
    url: "https://vclabs.org",
    siteName: "VC Labs",
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Mirai by VC Labs - AI Startup Due Diligence That Shows Its Work",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Mirai | AI Startup Due Diligence That Shows Its Work",
    description:
      "Multi-model council scoring, persona swarm reaction, and scenario simulation for startup evaluation.",
    site: "@VCLabsAI",
    creator: "@VCLabsAI",
    images: ["/og-image.png"],
  },
  alternates: {
    canonical: "https://vclabs.org",
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
          <Analytics />
        </Providers>
      </body>
    </html>
  );
}

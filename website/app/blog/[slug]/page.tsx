import { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllSlugs, getPostBySlug } from "@/lib/blog";

interface Props {
  params: { slug: string };
}

export async function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPostBySlug(params.slug);
  if (!post) return {};

  return {
    title: post.title,
    description: post.description,
    keywords: post.keywords,
    openGraph: {
      title: post.title,
      description: post.description,
      url: `https://vclabs.org/blog/${post.slug}`,
      type: "article",
      publishedTime: post.date,
      authors: [post.author],
      images: post.image ? [{ url: post.image }] : ["/og-image.png"],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.description,
      site: "@VCLabsAI",
      creator: "@VCLabsAI",
      images: post.image ? [post.image] : ["/og-image.png"],
    },
    alternates: {
      canonical: `https://vclabs.org/blog/${post.slug}`,
    },
  };
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function BlogPostPage({ params }: Props) {
  const post = await getPostBySlug(params.slug);
  if (!post) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    author: {
      "@type": "Organization",
      name: post.author,
      url: "https://vclabs.org",
    },
    publisher: {
      "@type": "Organization",
      name: "VC Labs",
      url: "https://vclabs.org",
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://vclabs.org/blog/${post.slug}`,
    },
    image: post.image || "https://vclabs.org/og-image.png",
    keywords: post.keywords.join(", "),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <article className="max-w-3xl mx-auto px-5 py-16">
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-faint hover:text-blue transition-colors mb-8"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className="rotate-180"
          >
            <path
              d="M6 3l5 5-5 5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Back to Blog
        </Link>

        <header className="mb-10">
          <h1 className="font-display text-3xl md:text-4xl lg:text-[2.75rem] text-ink leading-tight mb-4">
            {post.title}
          </h1>
          <div className="flex items-center gap-3 text-sm text-ink-faint">
            <time>{formatDate(post.date)}</time>
            <span className="w-1 h-1 rounded-full bg-ink-faint" />
            <span>{post.readTime}</span>
            <span className="w-1 h-1 rounded-full bg-ink-faint" />
            <span>{post.author}</span>
          </div>
        </header>

        <div
          className="prose prose-ink"
          dangerouslySetInnerHTML={{ __html: post.content }}
        />

        <div className="mt-16 rounded-lg border border-[var(--line)] bg-[var(--card)] p-8 text-center">
          <h3 className="font-display text-2xl text-ink mb-3">
            Ready to try AI-powered due diligence?
          </h3>
          <p className="text-ink-soft mb-6 max-w-lg mx-auto">
            Submit a startup to Mirai and get a research-backed analysis with
            multi-model scoring, swarm intelligence, and scenario simulation.
          </p>
          <Link href="/submit" className="btn-primary px-8 text-sm">
            Try Mirai Free
          </Link>
        </div>
      </article>
    </>
  );
}

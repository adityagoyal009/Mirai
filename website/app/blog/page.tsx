import { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog | VC Labs",
  description:
    "Insights on AI-powered startup due diligence, venture capital tools, and investment analysis from the VC Labs team.",
  openGraph: {
    title: "Blog | VC Labs",
    description:
      "Insights on AI-powered startup due diligence, venture capital tools, and investment analysis.",
    url: "https://vclabs.org/blog",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Blog | VC Labs",
    description:
      "Insights on AI-powered startup due diligence, venture capital tools, and investment analysis.",
    site: "@VCLabsAI",
  },
  alternates: {
    canonical: "https://vclabs.org/blog",
  },
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogPage() {
  const posts = getAllPosts();

  return (
    <section className="max-w-container-wide mx-auto px-5 py-16">
      <div className="max-w-3xl mx-auto text-center mb-14">
        <h1 className="font-display text-4xl md:text-5xl text-ink mb-4">
          Blog
        </h1>
        <p className="text-ink-soft text-lg">
          Insights on AI-powered due diligence, venture capital, and startup
          evaluation from the VC Labs team.
        </p>
      </div>

      <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 max-w-[1100px] mx-auto">
        {posts.map((post) => (
          <Link
            key={post.slug}
            href={`/blog/${post.slug}`}
            className="group block rounded-lg border border-[var(--line)] bg-[var(--card)] p-6 card-hover"
          >
            <time className="text-xs font-medium text-ink-faint uppercase tracking-wide">
              {formatDate(post.date)}
            </time>
            <h2 className="mt-2 text-lg font-bold text-ink leading-snug group-hover:text-blue transition-colors">
              {post.title}
            </h2>
            <p className="mt-2 text-sm text-ink-soft leading-relaxed line-clamp-3">
              {post.description}
            </p>
            <div className="mt-4 flex items-center gap-3 text-xs text-ink-faint">
              <span>{post.readTime}</span>
              <span className="w-1 h-1 rounded-full bg-ink-faint" />
              <span>{post.author}</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

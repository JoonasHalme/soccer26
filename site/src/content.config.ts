import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const matches = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/matches" }),
  schema: z.object({
    match_id: z.string(),
    title: z.string(),
    summary: z.string().optional(),
    verify_before_betting: z.array(z.string()).default([]),
    last_updated: z.string().optional(),
  }),
});

export const collections = { matches };

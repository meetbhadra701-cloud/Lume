/**
 * Seed passages for the "Load demo passage" button.
 * All passages are ≥50 words (required for logging gate).
 * Sources: Project Gutenberg public domain texts.
 */

export interface SeedPassage {
  id: string;
  title: string;
  source: string;
  text: string;
}

export const SEED_PASSAGES: SeedPassage[] = [
  {
    id: "gutenberg_001",
    title: "The Time Machine (H.G. Wells)",
    source: "Project Gutenberg — public domain",
    text: `The Time Traveller, for so it will be convenient to speak of him, was expounding a recondite matter to us. His grey eyes shone and twinkled, and his usually pale face was flushed and animated. The fire burned brightly, and the soft radiance of the incandescent lights in the lilies of silver caught the bubbles that flashed and passed in our glasses. Our chairs, being his patents, embraced and caressed us rather than submitted to be sat upon.`,
  },
  {
    id: "gutenberg_002",
    title: "The Adventures of Tom Sawyer (Mark Twain)",
    source: "Project Gutenberg — public domain",
    text: `Tom appeared on the sidewalk with a bucket of whitewash and a long-handled brush. He surveyed the fence, and all gladness left him and a deep melancholy settled down upon his spirit. Thirty yards of board fence nine feet high. Life to him seemed hollow, and existence but a burden. Sighing, he dipped his brush and passed it along the topmost plank; repeated the operation; did it again; compared the insignificant whitewashed streak with the far-reaching continent of unwhitewashed fence, and sat down on a tree-box discouraged.`,
  },
  {
    id: "gutenberg_003",
    title: "Pride and Prejudice (Jane Austen)",
    source: "Project Gutenberg — public domain",
    text: `It is a truth universally acknowledged, that a single man in possession of a good fortune must be in want of a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters. My dear Mr. Bennet, said his lady to him one day, have you heard that Netherfield Park is let at last?`,
  },
  {
    id: "gutenberg_004",
    title: "Moby Dick (Herman Melville)",
    source: "Project Gutenberg — public domain",
    text: `Call me Ishmael. Some years ago — never mind how long precisely — having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every funeral I meet; I account it high time to get to sea as soon as I can.`,
  },
  {
    id: "gutenberg_005",
    title: "Frankenstein (Mary Shelley)",
    source: "Project Gutenberg — public domain",
    text: `You will rejoice to hear that no disaster has accompanied the commencement of an enterprise which you have regarded with such evil forebodings. I arrived here yesterday, and my first task is to assure my dear sister of my welfare and increasing confidence in the success of my undertaking. I am already far north of London, and as I walk in the streets of Petersburgh, I feel a cold northern breeze play upon my cheeks, which braces my nerves and fills me with delight. Do you understand this feeling? This breeze, which has travelled from the regions towards which I am advancing, gives me a foretaste of those icy climes.`,
  },
  {
    id: "gutenberg_006",
    title: "The Hound of the Baskervilles (Arthur Conan Doyle)",
    source: "Project Gutenberg — public domain",
    text: `Mr. Sherlock Holmes, who was usually very late in the mornings, save upon those not infrequent occasions when he was up all night, was seated at the breakfast table. I stood upon the hearth-rug and picked up the stick which our visitor had left behind him the night before. It was a fine, thick piece of wood, bulbous-headed, of the sort which is known as a Penang lawyer. Just under the head was a broad silver band nearly an inch across. To James Mortimer, M.R.C.S., from his friends of the C.C.H., was engraved upon it, with the date 1884. It was just such a stick as the old-fashioned family practitioner used to carry — dignified, solid, and reassuring.`,
  },
  {
    id: "gutenberg_007",
    title: "Walden (Henry David Thoreau)",
    source: "Project Gutenberg — public domain",
    text: `I went to the woods because I wished to live deliberately, to front only the essential facts of life, and see if I could not learn what it had to teach, and not, when I came to die, discover that I had not lived. I did not wish to live what was not life, living is so dear; nor did I wish to practise resignation, unless it was quite necessary. I wanted to live deep and suck out all the marrow of life, to live so sturdily and Spartan-like as to put to rout all that was not life, to cut a broad swath and shave close, to drive life into a corner, and reduce it to its lowest terms.`,
  },
];

export function getRandomSeedPassage(): SeedPassage {
  return SEED_PASSAGES[Math.floor(Math.random() * SEED_PASSAGES.length)];
}

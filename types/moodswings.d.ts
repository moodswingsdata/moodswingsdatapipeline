/**
 * Data models for Mood Swings card data.
 *
 * These interfaces document the shape of Card, Printing, and Edition records
 * as produced by the moodswings data pipeline (YAML output).
 */

/**
 * Semantic version of the data schema as a [major, minor, patch] tuple.
 */
export const SCHEMA_VERSION: readonly [0, 9, 0];

/**
 * Marks a record whose data was corrected from what was originally printed.
 *
 * Errata is fundamentally a printing-side notion: a printing's as-printed text
 * can differ from the card's oracle (canonical) text. The correction is
 * reflected in the oracle field; this marker records that the correction
 * happened so downstream apps can choose how to display it.
 */
export interface Errata {
  /** Names of the fields that were corrected by this erratum. */
  fields: string[];

  /** Human-readable explanation of the correction. */
  note: string;
}

/**
 * A unique card identity with its game-mechanical properties.
 */
export interface Card {
  /** Stable UUID5 generated from the card name. */
  id: string;

  /** The card's display name. */
  name: string;

  /** Card colors: e.g. ['White'], ['Blue', 'Black'], or [] for colorless. */
  color: ("White" | "Blue" | "Black" | "Red" | "Green")[];

  /** Primary dice notation, e.g. '[3]' or '[6][1]'. Null for helper cards. */
  dice: string | null;

  /** Integer sum of pips in the primary dice. 0 if dice is null. */
  dice_value: number;

  /** Secondary dice notation after '/', or null. */
  secondary_dice: string | null;

  /** Integer sum of pips in the secondary dice. 0 if secondary_dice is null. */
  secondary_dice_value: number;

  /** Oracle (canonical) HTML-formatted rules text, or null for vanilla cards. */
  rules_text: string | null;

  /** List of note strings, or null if no notes exist. */
  notes: string[] | null;

  /** Errata applied to this card's oracle data, or null if there is none. */
  errata: Errata | null;
}

/**
 * An edition or set of cards.
 */
export interface Edition {
  /** Stable UUID5 generated from set_code. */
  id: string;

  /** Set code, e.g. 'MSW'. */
  set_code: string;

  /** Human-readable edition name, e.g. 'Edition 1'. */
  edition_name: string;

  /** When this set first came out. */
  release_date: Date;

  /** Language code, like 'en' or 'es-mx'. */
  language: string;
}

/**
 * A specific physical printing of a card.
 */
export interface Printing {
  /** Stable UUID5 generated from card_name:set_code:collector_number. Null until collector_number is known. */
  id: string | null;

  /** References the Card.id this printing belongs to. */
  card_id: string;

  /** References the Edition.id this printing belongs to. */
  edition_id: string;

  /** Frame color/style. */
  frame: "White" | "Blue" | "Black" | "Red" | "Green";

  /** Reminder icon glyph (e.g. '!') or null. */
  reminder_icon: string | null;

  /** Card rarity. */
  rarity: "Common" | "Uncommon" | "Rare" | "Mythic Rare";

  /** Color of the physical die: 'white', 'black', or null if unknown. */
  dice_color: "white" | "black" | null;

  /** Collector number within the set, or null if unknown. */
  collector_number: number | null;

  /** Print treatment, e.g. 'Standard', 'Foil'. */
  treatment: string;

  /** Artist name, array for multi-artist credits, or null if unknown. */
  artist: string | string[] | null;

  /** URL to the card image, or null if unavailable. */
  card_image_url: string | null;

  /**
   * Rules text exactly as physically printed on this printing, or null when it
   * is identical to the card's oracle rules_text. Populated when an erratum
   * means the printed text differs from the corrected oracle text.
   */
  printed_rules_text: string | null;

  /**
   * Errata recorded for this printing (e.g. the printed text differs from the
   * oracle), or null if there is none.
   */
  errata: Errata | null;
}

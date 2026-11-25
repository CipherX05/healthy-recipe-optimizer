// ─────────────────────────────────────────────────────────────
// Healthy Recipe Optimizer — demo dataset & scoring engine
// Mirrors the project pipeline: nutrition + flavor + cuisine + category
// ─────────────────────────────────────────────────────────────

export type Cuisine = 'indian' | 'italian' | 'american' | 'chinese' | 'mediterranean';

export const CUISINE_LABEL: Record<Cuisine, string> = {
  indian: 'Indian',
  italian: 'Italian',
  american: 'American',
  chinese: 'Chinese',
  mediterranean: 'Mediterranean',
};

export type GoalId = 'calories' | 'satFat' | 'protein' | 'fiber';

export interface Goal {
  id: GoalId;
  label: string;
  unit: string;
  direction: 'min' | 'max';
}

export const GOALS: Goal[] = [
  { id: 'satFat', label: 'Reduce saturated fat', unit: 'g', direction: 'min' },
  { id: 'calories', label: 'Reduce calories', unit: 'kcal', direction: 'min' },
  { id: 'protein', label: 'Increase protein', unit: 'g', direction: 'max' },
  { id: 'fiber', label: 'Increase fiber', unit: 'g', direction: 'max' },
];

// fixed flavor dimensions
export type FlavorVec = [number, number, number, number, number, number];
// [creamy, buttery/rich, umami, sweet, tangy/acid, earthy/spicy]

export interface Nutrients {
  calories: number; // kcal / 100g
  fat: number;
  satFat: number;
  protein: number;
  carbs: number;
  fiber: number;
}

export interface Ingredient {
  id: string;
  name: string;
  category: string;
  per100g: Nutrients;
  flavor: FlavorVec;
  cuisine: Partial<Record<Cuisine, number>>; // 0..1 affinity
}

export const INGREDIENTS: Record<string, Ingredient> = {
  butter: {
    id: 'butter', name: 'Butter', category: 'fat · dairy',
    per100g: { calories: 717, fat: 81, satFat: 51, protein: 0.9, carbs: 0.1, fiber: 0 },
    flavor: [0.95, 1.0, 0.1, 0.2, 0.1, 0.0],
    cuisine: { indian: 0.9, italian: 0.7, american: 0.85, chinese: 0.15, mediterranean: 0.5 },
  },
  ghee: {
    id: 'ghee', name: 'Ghee', category: 'fat · dairy',
    per100g: { calories: 900, fat: 100, satFat: 62, protein: 0, carbs: 0, fiber: 0 },
    flavor: [0.85, 0.95, 0.15, 0.15, 0.05, 0.1],
    cuisine: { indian: 1.0, italian: 0.2, american: 0.3, chinese: 0.1, mediterranean: 0.3 },
  },
  oliveOil: {
    id: 'oliveOil', name: 'Olive oil', category: 'fat · plant',
    per100g: { calories: 884, fat: 100, satFat: 14, protein: 0, carbs: 0, fiber: 0 },
    flavor: [0.35, 0.55, 0.1, 0.1, 0.15, 0.45],
    cuisine: { indian: 0.35, italian: 0.95, american: 0.6, chinese: 0.2, mediterranean: 1.0 },
  },
  avocadoPuree: {
    id: 'avocadoPuree', name: 'Avocado purée', category: 'fat · fruit',
    per100g: { calories: 160, fat: 15, satFat: 2.1, protein: 2, carbs: 9, fiber: 6.7 },
    flavor: [0.8, 0.55, 0.1, 0.1, 0.1, 0.35],
    cuisine: { indian: 0.25, italian: 0.4, american: 0.7, chinese: 0.1, mediterranean: 0.6 },
  },
  coconutOil: {
    id: 'coconutOil', name: 'Coconut oil', category: 'fat · plant',
    per100g: { calories: 892, fat: 100, satFat: 82, protein: 0, carbs: 0, fiber: 0 },
    flavor: [0.5, 0.6, 0.0, 0.35, 0.0, 0.1],
    cuisine: { indian: 0.6, italian: 0.1, american: 0.35, chinese: 0.2, mediterranean: 0.2 },
  },
  cream: {
    id: 'cream', name: 'Heavy cream', category: 'dairy',
    per100g: { calories: 340, fat: 36, satFat: 23, protein: 2.8, carbs: 2.8, fiber: 0 },
    flavor: [1.0, 0.8, 0.1, 0.25, 0.05, 0.0],
    cuisine: { indian: 0.85, italian: 0.8, american: 0.8, chinese: 0.1, mediterranean: 0.5 },
  },
  coconutCream: {
    id: 'coconutCream', name: 'Coconut cream', category: 'plant cream',
    per100g: { calories: 330, fat: 35, satFat: 31, protein: 3.6, carbs: 6.6, fiber: 2.2 },
    flavor: [0.9, 0.5, 0.05, 0.5, 0.0, 0.1],
    cuisine: { indian: 0.75, italian: 0.15, american: 0.3, chinese: 0.35, mediterranean: 0.2 },
  },
  evaporatedMilk: {
    id: 'evaporatedMilk', name: 'Evaporated milk (2%)', category: 'dairy',
    per100g: { calories: 107, fat: 4, satFat: 2.5, protein: 8, carbs: 11, fiber: 0 },
    flavor: [0.75, 0.45, 0.15, 0.4, 0.1, 0.0],
    cuisine: { indian: 0.6, italian: 0.5, american: 0.7, chinese: 0.2, mediterranean: 0.4 },
  },
  greekYogurt: {
    id: 'greekYogurt', name: 'Greek yogurt (low-fat)', category: 'dairy · fermented',
    per100g: { calories: 73, fat: 1.9, satFat: 1.2, protein: 10, carbs: 3.6, fiber: 0 },
    flavor: [0.7, 0.3, 0.2, 0.15, 0.75, 0.0],
    cuisine: { indian: 0.85, italian: 0.4, american: 0.6, chinese: 0.15, mediterranean: 0.9 },
  },
  cashewCream: {
    id: 'cashewCream', name: 'Cashew cream', category: 'plant cream',
    per100g: { calories: 180, fat: 14, satFat: 2.8, protein: 5.2, carbs: 9.5, fiber: 1.1 },
    flavor: [0.9, 0.55, 0.15, 0.3, 0.05, 0.25],
    cuisine: { indian: 0.8, italian: 0.45, american: 0.55, chinese: 0.3, mediterranean: 0.5 },
  },
  sourCream: {
    id: 'sourCream', name: 'Sour cream', category: 'dairy · fermented',
    per100g: { calories: 198, fat: 19, satFat: 12, protein: 2.4, carbs: 4.6, fiber: 0 },
    flavor: [0.85, 0.6, 0.15, 0.15, 0.8, 0.0],
    cuisine: { indian: 0.2, italian: 0.4, american: 0.9, chinese: 0.05, mediterranean: 0.45 },
  },
  cremeFraiche: {
    id: 'cremeFraiche', name: 'Crème fraîche', category: 'dairy · fermented',
    per100g: { calories: 292, fat: 30, satFat: 19, protein: 2.5, carbs: 3.1, fiber: 0 },
    flavor: [0.9, 0.75, 0.1, 0.15, 0.55, 0.0],
    cuisine: { indian: 0.15, italian: 0.5, american: 0.6, chinese: 0.05, mediterranean: 0.55 },
  },
  pancetta: {
    id: 'pancetta', name: 'Pancetta', category: 'cured meat',
    per100g: { calories: 407, fat: 35, satFat: 12.5, protein: 22, carbs: 0.5, fiber: 0 },
    flavor: [0.2, 0.75, 0.9, 0.1, 0.05, 0.3],
    cuisine: { indian: 0.05, italian: 1.0, american: 0.5, chinese: 0.2, mediterranean: 0.7 },
  },
  turkeyBacon: {
    id: 'turkeyBacon', name: 'Turkey bacon', category: 'cured meat',
    per100g: { calories: 226, fat: 16, satFat: 4.2, protein: 19, carbs: 1.5, fiber: 0 },
    flavor: [0.1, 0.5, 0.8, 0.1, 0.05, 0.35],
    cuisine: { indian: 0.05, italian: 0.45, american: 0.9, chinese: 0.2, mediterranean: 0.4 },
  },
  shiitake: {
    id: 'shiitake', name: 'Roasted shiitake', category: 'vegetable · fungi',
    per100g: { calories: 56, fat: 0.8, satFat: 0.2, protein: 2.2, carbs: 11, fiber: 3.8 },
    flavor: [0.15, 0.3, 0.95, 0.05, 0.05, 0.8],
    cuisine: { indian: 0.3, italian: 0.55, american: 0.5, chinese: 0.95, mediterranean: 0.5 },
  },
  parmesan: {
    id: 'parmesan', name: 'Parmesan', category: 'cheese · aged',
    per100g: { calories: 431, fat: 29, satFat: 18, protein: 38, carbs: 4.1, fiber: 0 },
    flavor: [0.25, 0.7, 0.95, 0.1, 0.2, 0.35],
    cuisine: { indian: 0.05, italian: 1.0, american: 0.75, chinese: 0.05, mediterranean: 0.85 },
  },
  nutritionalYeast: {
    id: 'nutritionalYeast', name: 'Nutritional yeast', category: 'seasoning',
    per100g: { calories: 325, fat: 5, satFat: 0.8, protein: 40, carbs: 35, fiber: 21 },
    flavor: [0.15, 0.5, 0.9, 0.05, 0.1, 0.4],
    cuisine: { indian: 0.1, italian: 0.5, american: 0.7, chinese: 0.15, mediterranean: 0.45 },
  },
  pecorino: {
    id: 'pecorino', name: 'Pecorino (½ portion)', category: 'cheese · aged',
    per100g: { calories: 200, fat: 14, satFat: 9, protein: 16, carbs: 2, fiber: 0 },
    flavor: [0.25, 0.65, 0.9, 0.05, 0.3, 0.35],
    cuisine: { indian: 0.05, italian: 0.95, american: 0.5, chinese: 0.05, mediterranean: 0.85 },
  },
  groundPork: {
    id: 'groundPork', name: 'Ground pork', category: 'meat',
    per100g: { calories: 297, fat: 24, satFat: 8.7, protein: 19, carbs: 0, fiber: 0 },
    flavor: [0.2, 0.65, 0.85, 0.05, 0.05, 0.2],
    cuisine: { indian: 0.1, italian: 0.7, american: 0.7, chinese: 0.95, mediterranean: 0.6 },
  },
  groundTurkey: {
    id: 'groundTurkey', name: 'Ground turkey (lean)', category: 'meat · poultry',
    per100g: { calories: 149, fat: 8, satFat: 2.1, protein: 20, carbs: 0, fiber: 0 },
    flavor: [0.15, 0.4, 0.7, 0.05, 0.05, 0.15],
    cuisine: { indian: 0.35, italian: 0.55, american: 0.9, chinese: 0.7, mediterranean: 0.6 },
  },
  tempeh: {
    id: 'tempeh', name: 'Crumbled tempeh', category: 'plant protein',
    per100g: { calories: 193, fat: 11, satFat: 2.5, protein: 19, carbs: 9.4, fiber: 7 },
    flavor: [0.2, 0.35, 0.8, 0.05, 0.1, 0.7],
    cuisine: { indian: 0.3, italian: 0.3, american: 0.55, chinese: 0.75, mediterranean: 0.4 },
  },
  redLentils: {
    id: 'redLentils', name: 'Red lentils', category: 'legume',
    per100g: { calories: 116, fat: 0.4, satFat: 0.1, protein: 9, carbs: 20, fiber: 7.9 },
    flavor: [0.35, 0.2, 0.4, 0.15, 0.05, 0.75],
    cuisine: { indian: 0.95, italian: 0.35, american: 0.4, chinese: 0.45, mediterranean: 0.7 },
  },
  caesarDressing: {
    id: 'caesarDressing', name: 'Caesar dressing', category: 'sauce · emulsion',
    per100g: { calories: 410, fat: 43, satFat: 6.5, protein: 1.6, carbs: 3.3, fiber: 0.2 },
    flavor: [0.8, 0.75, 0.6, 0.1, 0.55, 0.15],
    cuisine: { indian: 0.05, italian: 0.5, american: 0.95, chinese: 0.05, mediterranean: 0.5 },
  },
  yogurtCaesar: {
    id: 'yogurtCaesar', name: 'Yogurt Caesar dressing', category: 'sauce · emulsion',
    per100g: { calories: 130, fat: 9, satFat: 1.8, protein: 5, carbs: 6, fiber: 0.3 },
    flavor: [0.7, 0.45, 0.55, 0.1, 0.7, 0.1],
    cuisine: { indian: 0.15, italian: 0.45, american: 0.85, chinese: 0.05, mediterranean: 0.65 },
  },
  tahiniLemon: {
    id: 'tahiniLemon', name: 'Tahini–lemon dressing', category: 'sauce · emulsion',
    per100g: { calories: 220, fat: 19, satFat: 2.6, protein: 6, carbs: 8, fiber: 2.8 },
    flavor: [0.65, 0.5, 0.4, 0.05, 0.75, 0.5],
    cuisine: { indian: 0.25, italian: 0.35, american: 0.55, chinese: 0.15, mediterranean: 0.9 },
  },
  croutons: {
    id: 'croutons', name: 'Croutons', category: 'grain · baked',
    per100g: { calories: 407, fat: 6.6, satFat: 1.5, protein: 12, carbs: 74, fiber: 4.8 },
    flavor: [0.05, 0.4, 0.3, 0.1, 0.0, 0.5],
    cuisine: { indian: 0.05, italian: 0.6, american: 0.85, chinese: 0.05, mediterranean: 0.6 },
  },
  toastedChickpeas: {
    id: 'toastedChickpeas', name: 'Toasted chickpeas', category: 'legume',
    per100g: { calories: 164, fat: 2.6, satFat: 0.3, protein: 8.9, carbs: 27, fiber: 7.6 },
    flavor: [0.15, 0.25, 0.4, 0.1, 0.05, 0.7],
    cuisine: { indian: 0.8, italian: 0.4, american: 0.6, chinese: 0.3, mediterranean: 0.9 },
  },
  // ── non-replaceable recipe members ──
  chicken: {
    id: 'chicken', name: 'Chicken', category: 'meat · poultry',
    per100g: { calories: 165, fat: 3.6, satFat: 1, protein: 31, carbs: 0, fiber: 0 },
    flavor: [0.15, 0.45, 0.75, 0.05, 0.05, 0.15],
    cuisine: { indian: 0.95, italian: 0.7, american: 0.95, chinese: 0.9, mediterranean: 0.85 },
  },
  tomato: {
    id: 'tomato', name: 'Tomato', category: 'vegetable · fruit',
    per100g: { calories: 18, fat: 0.2, satFat: 0, protein: 0.9, carbs: 3.9, fiber: 1.2 },
    flavor: [0.05, 0.05, 0.55, 0.45, 0.85, 0.2],
    cuisine: { indian: 0.9, italian: 1, american: 0.8, chinese: 0.4, mediterranean: 0.95 },
  },
  onion: {
    id: 'onion', name: 'Onion', category: 'vegetable · allium',
    per100g: { calories: 40, fat: 0.1, satFat: 0, protein: 1.1, carbs: 9.3, fiber: 1.7 },
    flavor: [0.05, 0.1, 0.6, 0.4, 0.2, 0.5],
    cuisine: { indian: 0.95, italian: 0.85, american: 0.85, chinese: 0.8, mediterranean: 0.9 },
  },
  garlic: {
    id: 'garlic', name: 'Garlic', category: 'vegetable · allium',
    per100g: { calories: 149, fat: 0.5, satFat: 0.1, protein: 6.4, carbs: 33, fiber: 2.1 },
    flavor: [0.05, 0.1, 0.85, 0.1, 0.15, 0.85],
    cuisine: { indian: 0.95, italian: 0.95, american: 0.8, chinese: 0.95, mediterranean: 0.95 },
  },
  ginger: {
    id: 'ginger', name: 'Ginger', category: 'spice · rhizome',
    per100g: { calories: 80, fat: 0.8, satFat: 0.2, protein: 1.8, carbs: 18, fiber: 2 },
    flavor: [0.0, 0.05, 0.2, 0.2, 0.4, 0.95],
    cuisine: { indian: 0.95, italian: 0.1, american: 0.4, chinese: 0.95, mediterranean: 0.3 },
  },
  garamMasala: {
    id: 'garamMasala', name: 'Garam masala', category: 'spice blend',
    per100g: { calories: 325, fat: 12, satFat: 2, protein: 13, carbs: 48, fiber: 18 },
    flavor: [0.0, 0.1, 0.3, 0.25, 0.1, 1.0],
    cuisine: { indian: 1, italian: 0.05, american: 0.2, chinese: 0.15, mediterranean: 0.25 },
  },
  pasta: {
    id: 'pasta', name: 'Spaghetti (dry)', category: 'grain',
    per100g: { calories: 371, fat: 1.5, satFat: 0.3, protein: 13, carbs: 74, fiber: 3.2 },
    flavor: [0.2, 0.2, 0.2, 0.1, 0.0, 0.2],
    cuisine: { indian: 0.1, italian: 1, american: 0.8, chinese: 0.3, mediterranean: 0.8 },
  },
  egg: {
    id: 'egg', name: 'Eggs', category: 'protein · egg',
    per100g: { calories: 155, fat: 11, satFat: 3.3, protein: 13, carbs: 1.1, fiber: 0 },
    flavor: [0.7, 0.65, 0.5, 0.05, 0.05, 0.1],
    cuisine: { indian: 0.6, italian: 0.85, american: 0.9, chinese: 0.85, mediterranean: 0.8 },
  },
  blackPepper: {
    id: 'blackPepper', name: 'Black pepper', category: 'spice',
    per100g: { calories: 251, fat: 3.3, satFat: 1.4, protein: 10, carbs: 64, fiber: 25 },
    flavor: [0.0, 0.05, 0.2, 0.0, 0.1, 1.0],
    cuisine: { indian: 0.85, italian: 0.9, american: 0.9, chinese: 0.7, mediterranean: 0.85 },
  },
  beef: {
    id: 'beef', name: 'Beef sirloin', category: 'meat',
    per100g: { calories: 183, fat: 8.5, satFat: 3.4, protein: 27, carbs: 0, fiber: 0 },
    flavor: [0.15, 0.7, 0.95, 0.0, 0.05, 0.35],
    cuisine: { indian: 0.2, italian: 0.6, american: 0.95, chinese: 0.7, mediterranean: 0.6 },
  },
  mushroom: {
    id: 'mushroom', name: 'Mushrooms', category: 'vegetable · fungi',
    per100g: { calories: 22, fat: 0.3, satFat: 0.1, protein: 3.1, carbs: 3.3, fiber: 1 },
    flavor: [0.2, 0.25, 0.9, 0.05, 0.05, 0.75],
    cuisine: { indian: 0.4, italian: 0.8, american: 0.8, chinese: 0.9, mediterranean: 0.75 },
  },
  flour: {
    id: 'flour', name: 'Flour', category: 'grain',
    per100g: { calories: 364, fat: 1, satFat: 0.2, protein: 10, carbs: 76, fiber: 2.7 },
    flavor: [0.15, 0.1, 0.05, 0.1, 0.0, 0.1],
    cuisine: { indian: 0.8, italian: 0.9, american: 0.9, chinese: 0.7, mediterranean: 0.8 },
  },
  tofu: {
    id: 'tofu', name: 'Silken tofu', category: 'plant protein',
    per100g: { calories: 55, fat: 2.7, satFat: 0.4, protein: 5, carbs: 2.9, fiber: 0.3 },
    flavor: [0.75, 0.25, 0.35, 0.1, 0.05, 0.2],
    cuisine: { indian: 0.2, italian: 0.1, american: 0.4, chinese: 1.0, mediterranean: 0.2 },
  },
  doubanjiang: {
    id: 'doubanjiang', name: 'Doubanjiang', category: 'paste · fermented',
    per100g: { calories: 130, fat: 5, satFat: 0.8, protein: 8, carbs: 14, fiber: 3 },
    flavor: [0.1, 0.3, 0.95, 0.15, 0.2, 0.9],
    cuisine: { indian: 0.1, italian: 0.05, american: 0.2, chinese: 1.0, mediterranean: 0.1 },
  },
  chiliOil: {
    id: 'chiliOil', name: 'Sichuan chili oil', category: 'fat · infused',
    per100g: { calories: 884, fat: 100, satFat: 15, protein: 0, carbs: 0, fiber: 0 },
    flavor: [0.1, 0.4, 0.5, 0.0, 0.05, 1.0],
    cuisine: { indian: 0.4, italian: 0.1, american: 0.3, chinese: 1.0, mediterranean: 0.15 },
  },
  scallion: {
    id: 'scallion', name: 'Scallion', category: 'vegetable · allium',
    per100g: { calories: 32, fat: 0.2, satFat: 0, protein: 1.8, carbs: 7.3, fiber: 2.6 },
    flavor: [0.05, 0.05, 0.4, 0.2, 0.3, 0.6],
    cuisine: { indian: 0.5, italian: 0.3, american: 0.5, chinese: 0.95, mediterranean: 0.4 },
  },
  romaine: {
    id: 'romaine', name: 'Romaine lettuce', category: 'vegetable · leafy',
    per100g: { calories: 17, fat: 0.3, satFat: 0, protein: 1.2, carbs: 3.3, fiber: 2.1 },
    flavor: [0.1, 0.05, 0.1, 0.15, 0.1, 0.3],
    cuisine: { indian: 0.1, italian: 0.6, american: 0.9, chinese: 0.3, mediterranean: 0.8 },
  },
};

// ── recipes ──────────────────────────────────────────────────

export interface RecipeItem {
  ingredientId: string;
  grams: number;
  replaceable?: string[]; // candidate ingredient ids
}

export interface Recipe {
  id: string;
  name: string;
  cuisine: Cuisine;
  serves: number;
  note: string;
  items: RecipeItem[];
}

export const RECIPES: Recipe[] = [
  {
    id: 'butter-chicken',
    name: 'Butter Chicken',
    cuisine: 'indian',
    serves: 4,
    note: 'Murgh makhani — tomato, butter & cream',
    items: [
      { ingredientId: 'chicken', grams: 500 },
      { ingredientId: 'butter', grams: 60, replaceable: ['ghee', 'oliveOil', 'avocadoPuree', 'coconutOil'] },
      { ingredientId: 'cream', grams: 120, replaceable: ['coconutCream', 'evaporatedMilk', 'greekYogurt', 'cashewCream'] },
      { ingredientId: 'tomato', grams: 200 },
      { ingredientId: 'onion', grams: 150 },
      { ingredientId: 'garlic', grams: 15 },
      { ingredientId: 'ginger', grams: 15 },
      { ingredientId: 'garamMasala', grams: 10 },
    ],
  },
  {
    id: 'carbonara',
    name: 'Pasta Carbonara',
    cuisine: 'italian',
    serves: 4,
    note: 'Roman classic — egg, pecorino & pancetta',
    items: [
      { ingredientId: 'pasta', grams: 320 },
      { ingredientId: 'pancetta', grams: 150, replaceable: ['turkeyBacon', 'shiitake'] },
      { ingredientId: 'egg', grams: 200 },
      { ingredientId: 'parmesan', grams: 60, replaceable: ['nutritionalYeast', 'pecorino'] },
      { ingredientId: 'blackPepper', grams: 4 },
    ],
  },
  {
    id: 'stroganoff',
    name: 'Beef Stroganoff',
    cuisine: 'american',
    serves: 4,
    note: 'Sour-cream pan sauce with mushrooms',
    items: [
      { ingredientId: 'beef', grams: 500 },
      { ingredientId: 'butter', grams: 40, replaceable: ['ghee', 'oliveOil', 'avocadoPuree', 'coconutOil'] },
      { ingredientId: 'sourCream', grams: 200, replaceable: ['greekYogurt', 'cremeFraiche', 'cashewCream'] },
      { ingredientId: 'mushroom', grams: 200 },
      { ingredientId: 'onion', grams: 150 },
      { ingredientId: 'flour', grams: 20 },
    ],
  },
  {
    id: 'mapo-tofu',
    name: 'Mapo Tofu',
    cuisine: 'chinese',
    serves: 4,
    note: 'Sichuan — numbing chili-bean sauce',
    items: [
      { ingredientId: 'tofu', grams: 400 },
      { ingredientId: 'groundPork', grams: 150, replaceable: ['groundTurkey', 'tempeh', 'redLentils'] },
      { ingredientId: 'doubanjiang', grams: 45 },
      { ingredientId: 'chiliOil', grams: 30, replaceable: ['oliveOil'] },
      { ingredientId: 'garlic', grams: 10 },
      { ingredientId: 'scallion', grams: 20 },
    ],
  },
  {
    id: 'caesar',
    name: 'Caesar Salad',
    cuisine: 'american',
    serves: 4,
    note: 'Emulsified dressing, parmesan, crunch',
    items: [
      { ingredientId: 'romaine', grams: 300 },
      { ingredientId: 'caesarDressing', grams: 120, replaceable: ['yogurtCaesar', 'tahiniLemon'] },
      { ingredientId: 'parmesan', grams: 40, replaceable: ['nutritionalYeast', 'pecorino'] },
      { ingredientId: 'croutons', grams: 60, replaceable: ['toastedChickpeas'] },
    ],
  },
];

export const DEMO_EXAMPLE = {
  recipeId: 'butter-chicken',
  ingredientId: 'cream',
  goalId: 'satFat',
} as const;

// ── scoring engine ───────────────────────────────────────────

export function cosine(a: FlavorVec, b: FlavorVec): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  if (na === 0 || nb === 0) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

const sigmoid = (x: number) => 1 / (1 + Math.exp(-3 * x));

export function nutritionScore(orig: Ingredient, cand: Ingredient, goal: Goal): number {
  const o = orig.per100g[goal.id];
  const c = cand.per100g[goal.id];
  const raw = goal.direction === 'min' ? (o - c) / Math.max(o, 1e-6) : (c - o) / Math.max(o, 1e-6);
  return sigmoid(raw);
}

/** signed improvement fraction of `goal` when cand replaces orig (per 100g) */
export function goalImprovement(orig: Ingredient, cand: Ingredient, goal: Goal): number {
  const o = orig.per100g[goal.id];
  const c = cand.per100g[goal.id];
  return goal.direction === 'min' ? (o - c) / Math.max(o, 1e-6) : (c - o) / Math.max(o, 1e-6);
}

export interface CandidateScore {
  ingredient: Ingredient;
  flavor: number;
  nutrition: number;
  cuisine: number;
  category: number;
  overall: number;
  improvement: number; // recipe-level goal improvement if applied
}

const CATEGORY_MATCH: Record<string, Record<string, number>> = {
  'fat · dairy': { 'fat · dairy': 1, 'fat · plant': 0.75, 'fat · fruit': 0.65, 'dairy': 0.7 },
  'dairy': { 'dairy': 1, 'plant cream': 0.8, 'dairy · fermented': 0.85 },
  'dairy · fermented': { 'dairy · fermented': 1, 'dairy': 0.85, 'plant cream': 0.7 },
  'cured meat': { 'cured meat': 1, 'vegetable · fungi': 0.55, 'meat': 0.7 },
  'meat': { 'meat': 1, 'meat · poultry': 0.85, 'plant protein': 0.6, 'legume': 0.55 },
  'cheese · aged': { 'cheese · aged': 1, 'seasoning': 0.55 },
  'sauce · emulsion': { 'sauce · emulsion': 1 },
  'grain · baked': { 'grain · baked': 1, 'legume': 0.6 },
  'fat · infused': { 'fat · infused': 1, 'fat · plant': 0.7 },
};

function categoryScore(orig: Ingredient, cand: Ingredient): number {
  return CATEGORY_MATCH[orig.category]?.[cand.category] ?? 0.45;
}

export const WEIGHTS = { flavor: 0.35, nutrition: 0.3, cuisine: 0.25, category: 0.1 };

export function rankCandidates(recipe: Recipe, item: RecipeItem, goal: Goal): CandidateScore[] {
  const orig = INGREDIENTS[item.ingredientId];
  if (!item.replaceable) return [];
  return item.replaceable
    .map((cid) => {
      const cand = INGREDIENTS[cid];
      const flavor = cosine(orig.flavor, cand.flavor);
      const nutrition = nutritionScore(orig, cand, goal);
      const cuisine = cand.cuisine[recipe.cuisine] ?? 0.1;
      const category = categoryScore(orig, cand);
      const overall =
        WEIGHTS.flavor * flavor +
        WEIGHTS.nutrition * nutrition +
        WEIGHTS.cuisine * cuisine +
        WEIGHTS.category * category;
      // recipe-level improvement: compute actual nutrient difference directly
      const origRecipeVal = recipeNutrition(recipe)[goal.id];
      const modSubs: Record<string, string> = { [item.ingredientId]: cand.id };
      const modRecipeVal = recipeNutrition(recipe, modSubs)[goal.id];
      const rawDiff = goal.direction === 'min'
        ? origRecipeVal - modRecipeVal   // positive = less (good for 'min')
        : modRecipeVal - origRecipeVal;  // positive = more (good for 'max')
      const improvement = origRecipeVal > 1e-6
        ? rawDiff / origRecipeVal
        : (rawDiff > 0 ? 1 : rawDiff < 0 ? -1 : 0); // handle zero baseline
      return { ingredient: cand, flavor, nutrition, cuisine, category, overall, improvement };
    })
    .sort((a, b) => b.overall - a.overall);
}

export function recipeNutrition(recipe: Recipe, subs: Record<string, string> = {}): Nutrients {
  const total: Nutrients = { calories: 0, fat: 0, satFat: 0, protein: 0, carbs: 0, fiber: 0 };
  for (const it of recipe.items) {
    const ing = INGREDIENTS[subs[it.ingredientId] ?? it.ingredientId];
    const f = it.grams / 100;
    total.calories += ing.per100g.calories * f;
    total.fat += ing.per100g.fat * f;
    total.satFat += ing.per100g.satFat * f;
    total.protein += ing.per100g.protein * f;
    total.carbs += ing.per100g.carbs * f;
    total.fiber += ing.per100g.fiber * f;
  }
  return total;
}

export interface Optimization {
  subs: Record<string, string>; // originalId -> candidateId
  swaps: { from: Ingredient; to: Ingredient; grams: number; score: CandidateScore }[];
}

/** D2: apply the best eligible substitute in each selected slot, retaining its grams. */
export function optimizeRecipe(recipe: Recipe, goal: Goal, ingredientId?: string): Optimization {
  const subs: Record<string, string> = {};
  const swaps: Optimization['swaps'] = [];
  for (const it of recipe.items) {
    if (!it.replaceable || (ingredientId !== undefined && it.ingredientId !== ingredientId)) continue;
    const ranked = rankCandidates(recipe, it, goal);
    // walk ranked list (highest overall first) and pick the first that actually improves the goal
    const winner = ranked.find(
      (c) => goalImprovement(INGREDIENTS[it.ingredientId], c.ingredient, goal) > 0.02
    );
    if (winner) {
      subs[it.ingredientId] = winner.ingredient.id;
      swaps.push({ from: INGREDIENTS[it.ingredientId], to: winner.ingredient, grams: it.grams, score: winner });
    }
  }
  return { subs, swaps };
}

/** D3 — flavor similarity & cuisine consistency of modified recipe vs original */
export function recipeSimilarity(recipe: Recipe, opt: Optimization): { flavor: number; cuisine: number } {
  let totalGrams = 0, flavorAcc = 0, cuisineAcc = 0;
  for (const it of recipe.items) {
    const orig = INGREDIENTS[it.ingredientId];
    const subId = opt.subs[it.ingredientId];
    totalGrams += it.grams;
    if (subId) {
      const cand = INGREDIENTS[subId];
      flavorAcc += it.grams * cosine(orig.flavor, cand.flavor);
      cuisineAcc += it.grams * (cand.cuisine[recipe.cuisine] ?? 0.1);
    } else {
      flavorAcc += it.grams * 1;
      cuisineAcc += it.grams * (orig.cuisine[recipe.cuisine] ?? 0.5);
    }
  }
  return { flavor: flavorAcc / totalGrams, cuisine: cuisineAcc / totalGrams };
}

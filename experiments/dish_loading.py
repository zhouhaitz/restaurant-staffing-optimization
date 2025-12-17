"""Load dish recipes and menu distribution from JSON configuration file."""
import json
from pathlib import Path
from typing import Optional
from parameters import SingleDishParameters
from dish_recipes import validate_recipes


def load_recipes_from_json(json_path: str) -> SingleDishParameters:
    """Load dish recipes and menu distribution from a JSON file.
    
    Args:
        json_path: Path to JSON configuration file with 'dish_recipes' and 'menu_distribution' keys.
    
    Returns:
        SingleDishParameters instance with loaded recipes.
    
    Raises:
        FileNotFoundError: If JSON file doesn't exist.
        ValueError: If recipes are invalid or JSON structure is incorrect.
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"Recipe file not found: {json_path}")
    
    with open(json_path, 'r') as f:
        config = json.load(f)
    
    # Validate JSON structure
    if 'dish_recipes' not in config:
        raise ValueError("JSON must contain 'dish_recipes' key")
    if 'menu_distribution' not in config:
        raise ValueError("JSON must contain 'menu_distribution' key")
    
    # Convert JSON lists to tuples (required format)
    dish_recipes = {
        dish: [tuple(comp) for comp in components] 
        for dish, components in config['dish_recipes'].items()
    }
    
    # Validate recipes (checks station names, parameters, etc.)
    validate_recipes(dish_recipes)
    
    # Validate menu distribution matches recipes
    missing_dishes = set(config['menu_distribution'].keys()) - set(config['dish_recipes'].keys())
    if missing_dishes:
        raise ValueError(f"Menu distribution contains dishes not in recipes: {missing_dishes}")
    
    # Extract menu_catalog if present (optional)
    menu_catalog = config.get('menu_catalog')
    if menu_catalog:
        # Validate menu_catalog matches recipes
        catalog_dishes = set(menu_catalog.keys())
        recipe_dishes = set(config['dish_recipes'].keys())
        missing_in_catalog = recipe_dishes - catalog_dishes
        if missing_in_catalog:
            raise ValueError(f"Menu catalog missing dishes from recipes: {missing_in_catalog}")
        
        # Validate catalog structure
        for dish_name, catalog_entry in menu_catalog.items():
            if not isinstance(catalog_entry, dict):
                raise ValueError(f"Menu catalog entry for '{dish_name}' must be a dictionary")
            if 'price' not in catalog_entry:
                raise ValueError(f"Menu catalog entry for '{dish_name}' missing 'price'")
            if not isinstance(catalog_entry['price'], (int, float)) or catalog_entry['price'] < 0:
                raise ValueError(f"Menu catalog price for '{dish_name}' must be a non-negative number")
    
    # Create parameters
    params = SingleDishParameters(
        dish_recipes=dish_recipes,
        menu_distribution=config['menu_distribution'],
        menu_catalog=menu_catalog
    )
    
    return params


# Example usage: Load comal_recipes.json if running as script
if __name__ == '__main__':
    params = load_recipes_from_json('comal_recipes.json')
    print(f"Loaded {len(params.dish_recipes)} recipes successfully!")
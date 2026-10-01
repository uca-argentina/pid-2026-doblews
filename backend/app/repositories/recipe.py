"""Reaches a firm's own recipes, and only those (HU-9, ADR-006 rule 2).

Every write under /firms/{firm_id}/catalog/recipes resolves its recipe_id here.
The base select pins firm_id = :firm, which never matches a general recipe's
NULL nor another firm's id, so neither can be edited from a firm's routes.
"""

from app.models import Recipe
from app.repositories.base import FirmScopedRepository


class FirmRecipeRepository(FirmScopedRepository[Recipe]):
    """This firm's live recipes. Not the combined listing: that one also shows the
    general recipes, which is exactly what this repository exists to exclude, so it
    lives in app.services.catalog.list_recipes instead."""

    model = Recipe

    def get(self, recipe_id: int) -> Recipe | None:
        """The recipe to change, or None.

        None covers "does not exist", "is a general recipe", "belongs to another
        firm" and "already deactivated" alike: the route answers all four with the
        same 404, so a firm never learns which recipe ids exist elsewhere.
        """
        return self.db.scalars(self.select().where(Recipe.id == recipe_id)).first()

This is a new Django project named Pokedex. The objective of this app is to allow users to search for pokemon cards and save them to their personal collection.

We will build this application using the following tech stack: 

Python
Django
SQLite
uv
Tailwind CSS with DaisyUI using django-tailwind-cli
HTMX
Ruff
pytest


Here are the business requirements for the project:

1. Users should be able to save cards to their personal collection.
2. Users should be able to save cards they do not yet have to a wishlist
3. There should be an easy way for the user to filter their card collection by set, name, and rarity.
4. Users should be able to search a catalog of cards within specific sets, names, or raritys to more easily find what they are looking for.
5. Users can find their items through the external API we have chosen, TCGdex.
6. Users can save selected items to your application. Store enough information locally for saved items to remain accessible when the external API is unavailable.
7. Users can add and edit their own information.
8. Users can browse their saved items on a website. Include search, filtering, sorting, and pagination. These features must operate on locally saved data
9. Users must sign in to manage their saved data. Only they can modify their data. 
10. This application must provide its own API. Support listing, creating, updating, and deleting saved entries. Another program should be able to access this app's API and use it. 
11. The application handles unsuccessful external requests. Show a useful message when the provider is unavailable or a request fails. 
12. Card prices should be shown as a detail on cards, including in search results and in user collections. Users should be able to track the total value of their card collection.


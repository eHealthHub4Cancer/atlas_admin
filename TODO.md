# Implementation TODO: Role & Prefix Management System

## Backend Changes

### Models & Database
- [x] 1. Add Prefix model to models.py
- [x] 2. Update User model - change prefix to ForeignKey
- [x] 3. Simplify Role model - remove SEC sync fields
- [x] 4. Create migration file

### API Layer
- [x] 5. Create Prefix serializer in serializers.py
- [x] 6. Update Role serializer (remove SEC fields)
- [x] 7. Add Prefix CRUD views in api_views.py
- [x] 8. Add Role CRUD views in api_views.py
- [x] 9. Update API URLs in urls.py

### Business Logic
- [ ] 10. Update forms.py - dynamic querysets for Role/Prefix
- [ ] 11. Remove SEC sync calls from views.py
- [x] 12. Update seed_atlas.py - fix models and add default data

## Frontend Changes

### Type Definitions
- [ ] 13. Add Role and Prefix interfaces to types/index.ts
- [ ] 14. Update User interface to use new prefix structure

### API Integration
- [ ] 15. Add prefix/role API calls to lib/api.ts
- [ ] 16. Create custom hooks for prefixes/roles

### Pages & Components
- [ ] 17. Update SignupPage.tsx - fetch dynamic options
- [ ] 18. Create PrefixesPage.tsx - CRUD interface
- [ ] 19. Update RolesPage.tsx - add CRUD, remove SEC sync
- [ ] 20. Update AdminLayout.tsx - add Prefixes nav link
- [ ] 21. Add routes in App.tsx

## Testing & Deployment
- [ ] 22. Run migrations
- [ ] 23. Run seed command
- [ ] 24. Test signup with dynamic roles/prefixes
- [ ] 25. Test admin CRUD operations

---

## Progress Notes
- Started: Implementation in progress
- Current Step: 13 - Updating frontend types
- Backend completed: Models, serializers, API views, URLs, migration, seed
- Next: Update frontend to use new dynamic roles/prefixes

## Migration Commands
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Seed default data
python manage.py seed_atlas
```

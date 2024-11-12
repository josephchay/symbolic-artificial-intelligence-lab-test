from ortools.sat.python import cp_model

class ModelState:
    def __init__(self, model, x, y):
        self.model = model
        self.x = x
        self.y = y


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, x, y, person, shops, display_options):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._x = x
        self._y = y
        self._person = person
        self._shops = shops
        self._display_options = display_options
        self._solution_count = 0

    def print_shop_header(self, shop_type, items):
        print(f"\n{shop_type}")
        header = "Person    | " + " | ".join(item.ljust(8) for item in items)
        print(header)
        print("-" * len(header))

    def on_solution_callback(self):
        self._solution_count += 1
        print(f'\nSolution {self._solution_count}:')
        
        # Print tables based on display options
        for shop_name, shop_items in self._shops.items():
            if shop_name in self._display_options['shops']:
                self.print_shop_header(shop_name, list(shop_items.keys()))
                for n in range(len(self._person)):
                    if list(self._person.keys())[n] in self._display_options['people']:
                        person_name = list(self._person)[n].ljust(9)
                        selections = ["N/A".ljust(8) for _ in range(len(shop_items))]
                        
                        if shop_name == "Fruit Shop":
                            selections[self.Value(self._x[n])] = "Selected".ljust(8)
                        elif shop_name == "Dish Shop" and n == self._person['Bobby']:
                            selections[self.Value(self._y[0])] = "Selected".ljust(8)
                        
                        print(f"{person_name}| {' | '.join(selections)}")

    def solution_count(self):
        return self._solution_count

def get_user_input(prompt, options=None, allow_skip=True, allow_multiple=False):
    while True:
        print(f"\n{prompt}")
        if options:
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
        if allow_skip:
            print("(Press Enter to skip)")
        if allow_multiple:
            print("(For multiple selections, enter numbers separated by spaces, e.g., '1 3 4')")
        
        user_input = input("> ").strip()
        
        if allow_skip and user_input == "":
            return [] if allow_multiple else None
            
        try:
            if allow_multiple:
                selections = [int(x) for x in user_input.split()]
                result = [options[i-1] for i in selections if 1 <= i <= len(options)]
                if result:
                    return result
                print("No valid selections made. Please try again.")
            else:
                if not options:
                    return user_input
                selection = int(user_input)
                if 1 <= selection <= len(options):
                    return options[selection-1]
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            if not options and not allow_multiple:
                return user_input
            print("Invalid input. Please enter number(s).")
        continue

def print_current_constraints(current_constraints):
    if current_constraints:
        print("\nCurrent Constraints:")
        print("\nDefault Constraints:")
        for i, constraint in enumerate(current_constraints, 1):
            if constraint.get('is_default', False):
                print(f"{i}. {constraint['description']}")
                if constraint.get('more_description'):
                    print(f"   Strict Preference: {constraint['more_description']}")
        
        print("\nCustom Constraints:")
        custom_exists = False
        for i, constraint in enumerate(current_constraints, 1):
            if not constraint.get('is_default', False):
                custom_exists = True
                print(f"{i}. {constraint['description']}")
                if constraint.get('more_description'):
                    print(f"   Note: {constraint['more_description']}")
        if not custom_exists:
            print("No custom constraints added yet.")
    else:
        print("\nNo constraints defined.")

def check_constraint_conflicts(new_constraint, current_constraints):
    conflicts = []
    
    for existing in current_constraints:
        # Check for conflicts between must_order and must_not_order
        if (new_constraint['type'] in ['must_order', 'must_not_order'] and 
            existing['type'] in ['must_order', 'must_not_order']):
            if (new_constraint['person1'] == existing['person1'] and 
                new_constraint['shop'] == existing['shop']):
                if new_constraint['type'] != existing['type']:
                    conflicts.append({
                        'constraint': existing,
                        'reason': f"Conflicts with: {existing['description']} (opposite order requirement)",
                        'is_opposite': True
                    })
                else:
                    conflicts.append({
                        'constraint': existing,
                        'reason': f"Duplicate constraint: {existing['description']}",
                        'is_duplicate': True
                    })

        # Check for direct opposites
        if ('person1' in new_constraint and 'person2' in new_constraint and 
            'person1' in existing and 'person2' in existing):
            
            # Check both orderings of people
            same_people = (
                (new_constraint['person1'] == existing['person1'] and 
                new_constraint['person2'] == existing['person2']) or
                (new_constraint['person1'] == existing['person2'] and 
                new_constraint['person2'] == existing['person1']) or
                # Add reverse order check
                (new_constraint['person2'] == existing['person1'] and 
                new_constraint['person1'] == existing['person2'])
            )
            
            same_shop = new_constraint.get('shop') == existing.get('shop')
            
            if same_people and same_shop:
                # Check for opposite types (same vs different)
                if (('same_selection' in new_constraint['type'] and 
                    'different_selection' in existing['type']) or
                    ('different_selection' in new_constraint['type'] and 
                    'same_selection' in existing['type'])):
                    conflicts.append({
                        'constraint': existing,
                        'reason': f"Direct opposite of: {existing['description']}",
                        'is_opposite': True,
                        'is_default': existing.get('is_default', False)
                    })
                # Check for duplicate constraints
                elif new_constraint['type'] == existing['type']:
                    conflicts.append({
                        'constraint': existing,
                        'reason': f"Duplicate constraint: {existing['description']}",
                        'is_duplicate': True
                    })
        
        # Check for opposite item selections
        elif ('items' in new_constraint and 'items' in existing and 
            new_constraint['person1'] == existing['person1'] and 
            new_constraint['shop'] == existing['shop']):
            if (new_constraint['type'] == 'must_select' and 
                existing['type'] == 'cannot_select'):
                common_items = set(new_constraint['items']) & set(existing['items'])
                if common_items:
                    conflicts.append({
                        'constraint': existing,
                        'reason': f"Conflicts with: {existing['description']} (opposite item selection)",
                        'is_opposite': True
                    })
    
    return conflicts

def create_default_constraints(model, x, y, person, shops):
    constraints = []
    
    # 1. Cathy will not pick Salak
    model.Add(x[person['Cathy']] != shops["Fruit Shop"]["Salak"])
    constraints.append({
        'type': 'cannot_select',
        'person1': 'Cathy',
        'shop': 'Fruit Shop',
        'items': ['Salak'],
        'description': 'Cathy will not pick Salak',
        'more_description': 'Cathy will not pick Salak',
        'is_default': True
    })
    
    # 2. Adam and Bobby must have different fruits
    model.Add(x[person['Adam']] != x[person['Bobby']])
    constraints.append({
        'type': 'different_selection',
        'person1': 'Adam',
        'person2': 'Bobby',
        'shop': 'Fruit Shop',
        'description': 'Adam must have difference selection from Bobby in Fruit Shop',
        'more_description': 'Adam and Bobby want to steal each other’s fruit, so they will order different fruit',
        'is_default': True
    })
    
    # 3. Adam and Cathy must have the same fruit
    model.Add(x[person['Adam']] == x[person['Cathy']])
    constraints.append({
        'type': 'same_selection',
        'person1': 'Adam',
        'person2': 'Cathy',
        'shop': 'Fruit Shop',
        'description': 'Adam must have same selection as Cathy in Fruit Shop',
        'more_description': 'Cathy likes to be unique in her choice and will not order the same fruit as anybody else, but with one exception: Adam and Cathy are actually best friends and always order the same fruit as each other',
        'is_default': True
    })
    
    # 4. Dean dislikes Quenepa
    model.Add(x[person['Dean']] != shops["Fruit Shop"]["Quenepa"])
    constraints.append({
        'type': 'cannot_select',
        'person1': 'Dean',
        'shop': 'Fruit Shop',
        'items': ['Quenepa'],
        'description': 'Dean cannot select Quenepa from Fruit Shop',
        'more_description': 'Dean dislikes Quenepa and will not order this fruit.',
        'is_default': True
    })
    
    return constraints

def add_custom_constraint(model_state, person, shops, current_constraints):
    while True:
        constraint_types = [
            "Same selection from specific shop",
            "Different selection from specific shop",
            "Must order from specific shop",
            "Must not order from specific shop",
            "Cannot select specific items",
            "Must select specific items",
            "Back to main menu"
        ]
        
        print("\n----- Adding New Constraint -----")
        constraint_choice = get_user_input("Select constraint type:", constraint_types, allow_skip=False)
        if constraint_choice == "Back to main menu":
            return

        try:
            person1 = get_user_input("Select first person:", list(person.keys()), allow_skip=False)
            if not person1:
                print("Person selection is required.")
                continue

            new_constraint = {
                'person1': person1,
                'type': constraint_choice.lower().replace(" ", "_"),
                'description': ''
            }
            
            # Add prompt for additional description
            more_description = get_user_input("Enter a strict preference explanation for this constraint")
            if more_description:
                new_constraint['more_description'] = more_description
            
            if "from specific shop" in constraint_choice:
                shop = get_user_input("Select shop:", list(shops.keys()), allow_skip=False)
                if not shop:
                    print("Shop selection is required.")
                    continue
                    
                new_constraint['shop'] = shop
                
                if "Same" in constraint_choice:
                    person2 = get_user_input("Select second person:", list(person.keys()), allow_skip=False)
                    if not person2:
                        print("Second person selection is required.")
                        continue
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have same selection as {person2} in {shop}"
                    
                    if shop == "Fruit Shop":
                        model_state.model.Add(model_state.x[person[person1]] == model_state.x[person[person2]])
                    elif shop == "Dish Shop" and all(p == "Bobby" for p in [person1, person2]):
                        model_state.model.Add(model_state.y[0] >= 0)
                    else:
                        print("Invalid shop selection for these people.")
                        continue
                        
                elif "Different" in constraint_choice:
                    person2 = get_user_input("Select second person:", list(person.keys()), allow_skip=False)
                    if not person2:
                        print("Second person selection is required.")
                        continue
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have different selection from {person2} in {shop}"
                    
                    if shop == "Fruit Shop":
                        model_state.model.Add(model_state.x[person[person1]] != model_state.x[person[person2]])
                    else:
                        print("This constraint is only applicable for Fruit Shop.")
                        continue
            
                elif "Must order from" in constraint_choice or "Must not order from" in constraint_choice:
                    if "Must order from" in constraint_choice:
                        new_constraint['type'] = 'must_order'
                        new_constraint['description'] = f"{person1} must order from {shop}"
                        
                        # For Fruit Shop, person must select one of the available fruits
                        if shop == "Fruit Shop":
                            bool_vars = []
                            for item in shops[shop].keys():
                                bool_var = model_state.model.NewBoolVar(f'{person1}_{item}')
                                bool_vars.append(bool_var)
                                model_state.model.Add(model_state.x[person[person1]] == 
                                                    shops[shop][item]).OnlyEnforceIf(bool_var)
                            model_state.model.Add(sum(bool_vars) == 1)
                            
                        # For Dish Shop, only Bobby can order dishes
                        elif shop == "Dish Shop":
                            bool_vars = []
                            for item in shops[shop].keys():
                                bool_var = model_state.model.NewBoolVar(f'bobby_{item}')
                                bool_vars.append(bool_var)
                                model_state.model.Add(model_state.y[0] == 
                                                    shops[shop][item]).OnlyEnforceIf(bool_var)
                            model_state.model.Add(sum(bool_vars) == 1)
                                
                    else:  # Must not order from
                        new_constraint['type'] = 'must_not_order'
                        new_constraint['description'] = f"{person1} must not order from {shop}"
                        
                        # Check if it conflicts with mandatory constraints
                        if person1 == "Bobby" and shop == "Dish Shop":
                            print("Cannot restrict Bobby from Dish Shop (default constraint).")
                            continue
                            
                        # For Fruit Shop, person cannot select any fruits
                        if shop == "Fruit Shop":
                            for item in shops[shop].keys():
                                model_state.model.Add(model_state.x[person[person1]] != shops[shop][item])
                    
            elif "Cannot select" in constraint_choice:
                shop = get_user_input("Select shop:", list(shops.keys()), allow_skip=False)
                if not shop:
                    print("Shop selection is required.")
                    continue
                    
                items = get_user_input(f"Select items from {shop} to restrict:",
                                     list(shops[shop].keys()),
                                     allow_multiple=True)
                if not items:
                    print("Must select at least one item.")
                    continue
                    
                new_constraint['shop'] = shop
                new_constraint['items'] = items
                new_constraint['description'] = f"{person1} cannot select {', '.join(items)} from {shop}"
                
                for item in items:
                    if shop == "Fruit Shop":
                        model_state.model.Add(model_state.x[person[person1]] != shops[shop][item])
                    elif shop == "Dish Shop" and person1 == "Bobby":
                        model_state.model.Add(model_state.y[0] != shops[shop][item])
                    else:
                        print("Invalid shop/person combination for this constraint.")
                        continue
                        
            elif "Must select" in constraint_choice:
                shop = get_user_input("Select shop:", list(shops.keys()), allow_skip=False)
                if not shop:
                    print("Shop selection is required.")
                    continue
                    
                items = get_user_input(f"Select allowed items from {shop}:",
                                     list(shops[shop].keys()),
                                     allow_multiple=True)
                if not items:
                    print("Must select at least one item.")
                    continue
                    
                new_constraint['shop'] = shop
                new_constraint['items'] = items
                new_constraint['description'] = f"{person1} must select one of {', '.join(items)} from {shop}"
                
                bool_vars = []
                for item in items:
                    bool_var = model_state.model.NewBoolVar(f'{person1}_{item}')
                    bool_vars.append(bool_var)
                    
                    if shop == "Fruit Shop":
                        model_state.model.Add(model_state.x[person[person1]] == shops[shop][item]).OnlyEnforceIf(bool_var)
                    elif shop == "Dish Shop" and person1 == "Bobby":
                        model_state.model.Add(model_state.y[0] == shops[shop][item]).OnlyEnforceIf(bool_var)
                    else:
                        print("Invalid shop/person combination for this constraint.")
                        continue
                
                model_state.model.Add(sum(bool_vars) == 1)

            # Validate constraint before adding
            if not new_constraint.get('description'):
                print("Invalid constraint configuration. Please try again.")
                continue

            # Check for conflicts
            conflicts = check_constraint_conflicts(new_constraint, current_constraints)
            if conflicts:
                print("\nFound conflicting constraints:")
                for conflict in conflicts:
                    print(conflict['reason'])
                    
                    # If it's an opposite or duplicate, automatically remove the old one
                    if conflict.get('is_opposite') or conflict.get('is_duplicate'):
                        if conflict['constraint'].get('is_default', False):
                            print(f"Warning: This conflicts with default constraint: {conflict['constraint']['description']}")
                            choice = get_user_input(
                                "Do you want to: ",
                                ["Override default constraint", "Cancel adding new constraint"],
                                allow_skip=False
                            )
                            if choice == "Cancel adding new constraint":
                                print("Cancelled adding new constraint.")
                                return
                        
                        current_constraints.remove(conflict['constraint'])
                        print(f"Removed conflicting constraint: {conflict['constraint']['description']}")
                
                # Add the new constraint and rebuild model
                current_constraints.append(new_constraint)
                
                # Rebuild the model completely
                new_model, new_x, new_y = rebuild_model(current_constraints, person, shops)
                model_state.model = new_model
                model_state.x = new_x
                model_state.y = new_y
                print(f"\nConstraint added and model rebuilt successfully.")
                return
            
            # No conflicts, add the new constraint normally
            current_constraints.append(new_constraint)
            print(f"\nConstraint added successfully: {new_constraint['description']}")
            return
            
        except Exception as e:
            print(f"Error adding constraint: {str(e)}")
            choice = get_user_input("Would you like to try again?", ["yes", "no"], allow_skip=False)
            if choice != "yes":
                return

def edit_constraint_description(current_constraints):
    print("\nSelect a constraint to edit its description:")
    print_current_constraints(current_constraints)
    
    constraint_list = [(i, c) for i, c in enumerate(current_constraints, 1)]
    selected = get_user_input("Enter constraint number (or press Enter to cancel):", 
                            [f"{i}. {c['description']}" for i, c in constraint_list],
                            allow_skip=True)
    
    if selected:
        idx = int(selected.split('.')[0]) - 1
        constraint = current_constraints[idx]
        
        print(f"\nCurrent description: {constraint['description']}")
        if constraint.get('more_description'):
            print(f"Current note: {constraint['more_description']}")
            
        new_description = get_user_input(
            "Enter new note (or press Enter to keep current):",
            allow_skip=True
        )
        
        if new_description:
            constraint['more_description'] = new_description
            print("Description updated successfully!")
        else:
            print("Description unchanged.")

def rebuild_model(current_constraints, default_person, shops):
    """Rebuilds the model from scratch with given constraints."""
    model = cp_model.CpModel()
    
    # Create variables
    x = [model.NewIntVar(0, len(shops["Fruit Shop"]) - 1, f'x_{i}') 
         for i in range(len(default_person))]
    y = [model.NewIntVar(0, len(shops["Dish Shop"]) - 1, 'bobby_dish')]

    # Add Bobby's dish constraint
    bobby_pasta = model.NewBoolVar('bobby_pasta')
    bobby_risotto = model.NewBoolVar('bobby_risotto')
    model.Add(y[0] == shops["Dish Shop"]["Pasta"]).OnlyEnforceIf(bobby_pasta)
    model.Add(y[0] == shops["Dish Shop"]["Risotto"]).OnlyEnforceIf(bobby_risotto)
    model.Add(bobby_pasta + bobby_risotto == 1)

    # Track which constraints have been applied
    applied_constraints = set()

    # Apply all constraints
    for constraint in current_constraints:
        constraint_key = f"{constraint['type']}_{constraint.get('person1', '')}_{constraint.get('person2', '')}_{constraint.get('shop', '')}"
        
        if constraint_key in applied_constraints:
            continue
            
        try:
            if 'cannot_select' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    for item in constraint['items']:
                        model.Add(x[default_person[constraint['person1']]] != 
                                shops[constraint['shop']][item])
                    
            elif 'same_selection' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    model.Add(x[default_person[constraint['person1']]] == 
                             x[default_person[constraint['person2']]])
                    
            elif 'different_selection' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    model.Add(x[default_person[constraint['person1']]] != 
                             x[default_person[constraint['person2']]])
                    
            elif 'must_order' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    bool_vars = []
                    for item in shops[constraint['shop']].keys():
                        bool_var = model.NewBoolVar(f"{constraint['person1']}_{item}")
                        bool_vars.append(bool_var)
                        model.Add(x[default_person[constraint['person1']]] == 
                                shops[constraint['shop']][item]).OnlyEnforceIf(bool_var)
                    model.Add(sum(bool_vars) == 1)
                elif constraint['shop'] == "Dish Shop" and constraint['person1'] == "Bobby":
                    bool_vars = []
                    for item in shops[constraint['shop']].keys():
                        bool_var = model.NewBoolVar(f"bobby_{item}")
                        bool_vars.append(bool_var)
                        model.Add(y[0] == shops[constraint['shop']][item]).OnlyEnforceIf(bool_var)
                    model.Add(sum(bool_vars) == 1)
                    
            elif 'must_not_order' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    for item in shops[constraint['shop']].keys():
                        model.Add(x[default_person[constraint['person1']]] != 
                                shops[constraint['shop']][item])
            elif 'must_select' in constraint['type']:
                if constraint['shop'] == "Fruit Shop":
                    bool_vars = []
                    for item in constraint['items']:
                        bool_var = model.NewBoolVar(f"{constraint['person1']}_{item}")
                        bool_vars.append(bool_var)
                        model.Add(x[default_person[constraint['person1']]] == 
                                shops[constraint['shop']][item]).OnlyEnforceIf(bool_var)
                    model.Add(sum(bool_vars) == 1)

            applied_constraints.add(constraint_key)
            
        except Exception as e:
            print(f"Warning: Failed to apply constraint {constraint['description']}: {str(e)}")
            continue

    return model, x, y

def display_menu():
    options = {
        'shops': get_user_input("Select shops to display:",
                              ["Fruit Shop", "Dish Shop"],
                              allow_multiple=True),
        'people': get_user_input("Select people to display:",
                               ["Adam", "Bobby", "Cathy", "Dean"],
                               allow_multiple=True)
    }
    if not options['shops'] or not options['people']:
        return {
            'shops': ["Fruit Shop", "Dish Shop"],
            'people': ["Adam", "Bobby", "Cathy", "Dean"]
        }
    return options

def solve_assignment():
    try:
        # Default setup
        default_person = dict(Adam=0, Bobby=1, Cathy=2, Dean=3)
        shops = {
            "Fruit Shop": dict(Papaya=0, Quenepa=1, Rambutan=2, Salak=3),
            "Dish Shop": dict(Pasta=0, Risotto=1)
        }

        # First create the initial model
        model = cp_model.CpModel()
        x = [model.NewIntVar(0, len(shops["Fruit Shop"]) - 1, f'x_{i}') 
             for i in range(len(default_person))]
        y = [model.NewIntVar(0, len(shops["Dish Shop"]) - 1, 'bobby_dish')]

        # Now set up default constraints with all required arguments
        print("\nSetting up default constraints...")
        current_constraints = create_default_constraints(model, x, y, default_person, shops)
        
        # Create model state
        model_state = ModelState(model, x, y)

        # Add Bobby's dish constraint
        bobby_pasta = model_state.model.NewBoolVar('bobby_pasta')
        bobby_risotto = model_state.model.NewBoolVar('bobby_risotto')
        model_state.model.Add(model_state.y[0] == shops["Dish Shop"]["Pasta"]).OnlyEnforceIf(bobby_pasta)
        model_state.model.Add(model_state.y[0] == shops["Dish Shop"]["Risotto"]).OnlyEnforceIf(bobby_risotto)
        model_state.model.Add(bobby_pasta + bobby_risotto == 1)
        
        current_constraints.append({
            'type': 'must_order',
            'person1': 'Bobby',
            'shop': 'Dish Shop',
            'description': 'Bobby must select one of Pasta, Risotto from Dish Shop',
            'is_default': True
        })

        display_options = {
            'shops': ["Fruit Shop", "Dish Shop"],
            'people': ["Adam", "Bobby", "Cathy", "Dean"]
        }

        while True:
            print("\n========== Main Menu ==========")
            print("1. Add custom constraints")
            print("2. View current constraints")
            print("3. Set display options")
            print("4. Find solutions")
            print("5. Edit constraint descriptions")
            print("6. Exit")
            
            choice = input("> ").strip()
            
            if choice == "1":
                while True:
                    try:
                        num_str = get_user_input(
                            "How many custom constraints would you like to add?", 
                            allow_skip=False)
                        num_constraints = int(num_str)
                        if num_constraints <= 0:
                            print("Please enter a positive number.")
                            continue
                        break
                    except ValueError:
                        print("Please enter a valid number.")
                
                for i in range(num_constraints):
                    print(f"\nAdding constraint {i+1} of {num_constraints}")
                    add_custom_constraint(
                        model_state=model_state,
                        person=default_person,
                        shops=shops,
                        current_constraints=current_constraints
                    )
                
                # After adding constraints, rebuild the model and update model_state
                new_model, new_x, new_y = rebuild_model(current_constraints, default_person, shops)
                model_state.model = new_model
                model_state.x = new_x
                model_state.y = new_y
                
            elif choice == "2":
                print_current_constraints(current_constraints)
                    
            elif choice == "3":
                new_display_options = display_menu()
                if new_display_options:
                    display_options = new_display_options
                print("\nCurrent display options:")
                print(f"Shops: {', '.join(display_options['shops'])}")
                print(f"People: {', '.join(display_options['people'])}")
                    
            elif choice == "4":
                solution_menu_options = [
                    "Show all solutions",
                    "Show solutions for specific shops",
                    "Show solutions with specific items selected",
                    "Back to main menu"
                ]
                
                while True:
                    solution_choice = get_user_input("Select solution display option:", 
                                                   solution_menu_options, 
                                                   allow_skip=False)
                    
                    if solution_choice == "Back to main menu":
                        break
                        
                    temp_model = model_state.model.Clone()  # Use model_state.model instead of model
                    if solution_choice == "Show solutions for specific shops":
                        display_options['shops'] = get_user_input(
                            "Select shops to show solutions for:",
                            list(shops.keys()),
                            allow_multiple=True
                        )
                        display_options['people'] = get_user_input(
                            "Select people to show solutions for:",
                            list(default_person.keys()),
                            allow_multiple=True
                        )
                        
                    elif solution_choice == "Show solutions with specific items selected":
                        shop = get_user_input("Select shop:", list(shops.keys()))
                        items = get_user_input(
                            f"Select items to filter solutions for:",
                            list(shops[shop].keys()),
                            allow_multiple=True
                        )
                        person_name = get_user_input(
                            "Select person to filter solutions for:",
                            list(default_person.keys())
                        )
                        
                        # Add temporary constraint for filtering
                        if shop == "Fruit Shop":
                            bool_vars = []
                            for item in items:
                                bool_var = temp_model.NewBoolVar(f'filter_{person_name}_{item}')
                                bool_vars.append(bool_var)
                                temp_model.Add(model_state.x[default_person[person_name]] ==  # Use model_state.x
                                        shops[shop][item]).OnlyEnforceIf(bool_var)
                            temp_model.Add(sum(bool_vars) == 1)
                        elif shop == "Dish Shop" and person_name == "Bobby":
                            bool_vars = []
                            for item in items:
                                bool_var = temp_model.NewBoolVar(f'filter_bobby_{item}')
                                bool_vars.append(bool_var)
                                temp_model.Add(model_state.y[0] ==  # Use model_state.y
                                        shops[shop][item]).OnlyEnforceIf(bool_var)
                            temp_model.Add(sum(bool_vars) == 1)
                
                    solver = cp_model.CpSolver()
                    # Use model_state.x and model_state.y for the SolutionPrinter
                    solution_printer = SolutionPrinter(model_state.x, model_state.y, default_person, shops, display_options)
                    print("\nSearching for solutions...")
                    status = solver.SearchForAllSolutions(temp_model, solution_printer)
                    
                    print(f'\nTotal solutions found: {solution_printer.solution_count()}')
                    if status == cp_model.INFEASIBLE:
                        print('The problem is infeasible - no valid solutions exist with these constraints.')
                        print('\nCurrent constraints that might be causing the conflict:')
                        print_current_constraints(current_constraints)
                    
                    break
            elif choice == "5":
                edit_constraint_description(current_constraints)
            elif choice == "6":
                print("Goodbye!")
                return
            
            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please try again.")


if __name__ == '__main__':
    print("Welcome to the Food Constraint Satisfiability Problem (CSP)!")
    
    try:
        solve_assignment()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please try again.")

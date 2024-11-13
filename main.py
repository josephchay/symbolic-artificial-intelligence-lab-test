# Import required libraries
import tkinter as tk  # Main GUI library
from tkinter import ttk, messagebox, scrolledtext  # Additional GUI components
from ortools.sat.python import cp_model  # Google's constraint programming solver

class ModelState:
    """Class to maintain the state of the constraint satisfaction problem model"""
    def __init__(self, model, x, y):
        self.model = model  # The CP-SAT model instance
        self.x = x  # Variables for fruit shop selections
        self.y = y  # Variables for dish shop selections (specifically Bobby's selection)


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Callback class to handle and display solutions as they are found"""
    def __init__(self, x, y, person, shops, display_options, output_callback):
        cp_model.CpSolverSolutionCallback.__init__(self)  # Initialize parent class
        self._x = x  # Fruit shop decision variables
        self._y = y  # Dish shop decision variables
        self._person = person  # Dictionary mapping person names to indices
        self._shops = shops  # Dictionary containing shop items
        self._display_options = display_options  # Display preferences
        self._solution_count = 0  # Counter for number of solutions found
        self._output_callback = output_callback  # Function to write output to GUI

    def print_shop_header(self, shop_type, items):
        """Creates and displays the header for shop solutions
        Args:
            shop_type: Name of the shop
            items: List of items available in the shop
        """
        header = f"\n{shop_type}\n"
        header += "Person    | " + " | ".join(item.ljust(8) for item in items) + "\n"
        header += "-" * len(header) + "\n"
        self._output_callback(header)

    def on_solution_callback(self):
        """Called for each solution found by the solver
        Formats and displays the solution using the output callback"""
        self._solution_count += 1  # Increment solution counter
        self._output_callback(f'\nSolution {self._solution_count}:\n')
        
        # Iterate through each shop
        for shop_name, shop_items in self._shops.items():
            if shop_name in self._display_options['shops']:
                # Print shop header
                self.print_shop_header(shop_name, list(shop_items.keys()))
                
                # Process each person's selections
                for n in range(len(self._person)):
                    if list(self._person.keys())[n] in self._display_options['people']:
                        person_name = list(self._person)[n].ljust(9)
                        selections = ["N/A".ljust(8) for _ in range(len(shop_items))]
                        
                        # Handle different shops differently
                        if shop_name == "Fruit Shop":
                            selections[self.Value(self._x[n])] = "Selected".ljust(8)
                        elif shop_name == "Dish Shop" and n == self._person['Bobby']:
                            selections[self.Value(self._y[0])] = "Selected".ljust(8)
                        
                        self._output_callback(f"{person_name}| {' | '.join(selections)}\n")

    def solution_count(self):
        """Returns the total number of solutions found"""
        return self._solution_count


class GUIInputDialog:
    """Dialog window class for getting user input in various formats"""
    def __init__(self, parent, prompt, options=None, allow_skip=True, allow_multiple=False):
        # Initialize the dialog window
        self.dialog = tk.Toplevel(parent)  # Create new window on top of parent
        self.dialog.title("Input Required")  # Set window title
        self.dialog.geometry("400x300")  # Set window size
        self.dialog.transient(parent)  # Make dialog transient to parent (always stays on top of parent)
        self.dialog.grab_set()  # Modal window - must be dealt with before returning to parent
        
        # Initialize instance variables
        self.result = None  # Will store the user's input
        self.options = options  # List of options for selection-type dialogs
        self.allow_multiple = allow_multiple  # Whether multiple selections are allowed
        
        # Create and pack the prompt label
        ttk.Label(self.dialog, text=prompt, wraplength=350).pack(pady=5)
        
        # Handle different types of input dialogs
        if options:  # If options are provided, create a selection dialog
            if allow_multiple:  # For multiple selection (checkboxes)
                self.vars = []  # List to store checkbox variables
                frame = ttk.Frame(self.dialog)
                frame.pack(fill='both', expand=True, padx=5, pady=5)
                
                # Create scrollable canvas for options
                canvas = tk.Canvas(frame)
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                # Configure canvas scrolling
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                # Create window inside canvas
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Create checkboxes for each option
                for opt in options:
                    var = tk.BooleanVar()
                    self.vars.append(var)
                    ttk.Checkbutton(scrollable_frame, text=opt, variable=var).pack(pady=2)
                
                # Pack canvas and scrollbar
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
            else:  # For single selection (radio buttons)
                self.var = tk.StringVar()
                for opt in options:
                    ttk.Radiobutton(self.dialog, text=opt, 
                                  variable=self.var, value=opt).pack(pady=2)
        else:  # If no options provided, create a text entry dialog
            self.entry = ttk.Entry(self.dialog, width=50)
            self.entry.pack(pady=5)
        
        # Create button frame for OK/Skip buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side='bottom', pady=10)
        
        # Add OK and optional Skip buttons
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side='left', padx=5)
        if allow_skip:
            ttk.Button(button_frame, text="Skip", command=self.on_skip).pack(side='left', padx=5)
        
        # Center the dialog on parent window
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def on_ok(self):
        """Handle OK button click - save the user's input"""
        if self.options:  # For selection dialogs
            if self.allow_multiple:  # Multiple selection
                self.result = [opt for i, opt in enumerate(self.options) 
                             if self.vars[i].get()]
            else:  # Single selection
                self.result = self.var.get()
        else:  # For text entry
            self.result = self.entry.get()
        self.dialog.destroy()  # Close the dialog

    def on_skip(self):
        """Handle Skip button click - set empty/None result"""
        self.result = [] if self.allow_multiple else None  # Set appropriate empty result
        self.dialog.destroy()  # Close the dialog


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
    """Create and return the default constraints for the CSP problem
    
    Args:
        model: The CP-SAT model instance
        x: Variables for fruit shop selections
        y: Variables for dish shop selections
        person: Dictionary mapping person names to indices
        shops: Dictionary containing shop items
    
    Returns:
        List of constraint dictionaries containing the default rules
    """
    constraints = []
    
    # Constraint 1: Cathy cannot select Salak
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
    
    # Constraint 2: Adam and Bobby must choose different fruits
    model.Add(x[person['Adam']] != x[person['Bobby']])
    constraints.append({
        'type': 'different_selection',
        'person1': 'Adam',
        'person2': 'Bobby',
        'shop': 'Fruit Shop',
        'description': 'Adam must have difference selection from Bobby in Fruit Shop',
        'more_description': 'Adam and Bobby want to steal each other\'s fruit, so they will order different fruit',
        'is_default': True
    })
    
    # Constraint 3: Adam and Cathy must choose the same fruit
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
    
    # Constraint 4: Dean cannot select Quenepa
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


class CSPSolverGUI:
    """Main GUI class for the CSP Solver application"""
    def __init__(self, root):
        # Initialize main window
        self.root = root
        self.root.title("Food CSP Solver")
        self.root.geometry("1000x800")  # Set window size
        
        # Set up initial model state and data
        self.initialize_data()
        
        # Create main container with padding
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Create GUI elements
        self.create_output_area()  # Create text output area
        self.create_buttons()  # Create control buttons
        
        # Display welcome message
        self.write_output("Welcome to the Food Constraint Satisfaction Problem (CSP) Solver!\n")
        self.write_output("\nDefault constraints have been set up.\n")
        self.view_constraints()  # Show initial constraints

    def initialize_data(self):
        """Initialize all data structures and models for the CSP solver"""
        # Define people and their indices
        self.default_person = dict(Adam=0, Bobby=1, Cathy=2, Dean=3)
        
        # Define shops and their items with indices
        self.shops = {
            "Fruit Shop": dict(Papaya=0, Quenepa=1, Rambutan=2, Salak=3),
            "Dish Shop": dict(Pasta=0, Risotto=1)
        }
        
        # Create initial CP-SAT model
        model = cp_model.CpModel()
        
        # Create variables for fruit shop selections
        x = [model.NewIntVar(0, len(self.shops["Fruit Shop"]) - 1, f'x_{i}') 
             for i in range(len(self.default_person))]
             
        # Create variables for Bobby's dish selection
        y = [model.NewIntVar(0, len(self.shops["Dish Shop"]) - 1, 'bobby_dish')]
        
        # Set up default constraints
        self.current_constraints = create_default_constraints(model, x, y, 
                                                           self.default_person, self.shops)
        self.model_state = ModelState(model, x, y)

        # Add Bobby's special dish constraint
        bobby_pasta = self.model_state.model.NewBoolVar('bobby_pasta')  # Boolean variable for pasta selection
        bobby_risotto = self.model_state.model.NewBoolVar('bobby_risotto')  # Boolean variable for risotto selection
        
        # Add constraints for Bobby's dish selection
        self.model_state.model.Add(self.model_state.y[0] == 
                                 self.shops["Dish Shop"]["Pasta"]).OnlyEnforceIf(bobby_pasta)
        self.model_state.model.Add(self.model_state.y[0] == 
                                 self.shops["Dish Shop"]["Risotto"]).OnlyEnforceIf(bobby_risotto)
        self.model_state.model.Add(bobby_pasta + bobby_risotto == 1)  # Must choose exactly one dish
        
        # Add Bobby's dish constraint to constraints list
        self.current_constraints.append({
            'type': 'must_order',
            'person1': 'Bobby',
            'shop': 'Dish Shop',
            'description': 'Bobby must select one of Pasta, Risotto from Dish Shop',
            'more_description': 'Bobby will only order pasta or risotto',
            'is_default': True
        })
        
        # Initialize display options
        self.display_options = {
            'shops': ["Fruit Shop", "Dish Shop"],
            'people': ["Adam", "Bobby", "Cathy", "Dean"]
        }

    def create_output_area(self):
        """Create the scrolled text area for displaying outputs"""
        # Create labeled frame for output
        output_frame = ttk.LabelFrame(self.main_container, text="Output", padding="5")
        output_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        
        # Create scrolled text widget
        self.output_area = scrolledtext.ScrolledText(
            output_frame, 
            wrap=tk.WORD,  # Wrap text at word boundaries
            width=80, 
            height=30,
            font=('Courier', 10)  # Monospace font for better alignment
        )
        self.output_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.output_area.config(state='disabled')  # Make read-only initially

    def create_buttons(self):
        """Create the control buttons at the bottom of the window"""
        # Create frame for buttons
        button_frame = ttk.Frame(self.main_container, padding="5")
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Define buttons with their commands
        buttons = [
            ("Add Constraint", self.show_add_constraint_dialog),
            ("View Constraints", self.view_constraints),
            ("Find Solutions", self.show_solution_dialog),
            ("Edit Descriptions", self.show_edit_description_dialog),
            ("Exit", self.root.quit)
        ]
        
        # Create and grid each button
        for i, (text, command) in enumerate(buttons):
            btn = ttk.Button(button_frame, text=text, command=command, style='Action.TButton')
            btn.grid(row=0, column=i, padx=5)
            button_frame.grid_columnconfigure(i, weight=1)

    def write_output(self, text):
        """Write text to the output area
        
        Args:
            text: String to write to output
        """
        self.output_area.config(state='normal')  # Enable editing
        self.output_area.insert(tk.END, text)  # Insert text at end
        self.output_area.config(state='disabled')  # Disable editing
        self.output_area.see(tk.END)  # Scroll to show latest text

    def clear_output(self):
        """Clear all text from the output area"""
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')

    def get_user_input_gui(self, prompt, options=None, allow_skip=True, allow_multiple=False):
        """Show dialog to get user input
        
        Args:
            prompt: Text to show user
            options: List of options for selection (optional)
            allow_skip: Whether to show Skip button
            allow_multiple: Whether multiple selections are allowed
            
        Returns:
            User's input or None if skipped
        """
        dialog = GUIInputDialog(self.root, prompt, options, allow_skip, allow_multiple)
        self.root.wait_window(dialog.dialog)  # Wait for dialog to close
        return dialog.result

    def show_add_constraint_dialog(self):
        """Show dialog for adding a new constraint"""
        # Define available constraint types
        constraint_types = [
            "Same selection from specific shop",
            "Different selection from specific shop",
            "Must order from specific shop",
            "Must not order from specific shop",
            "Cannot select specific items",
            "Must select specific items"
        ]
        
        # Get constraint type from user
        constraint_choice = self.get_user_input_gui(
            "Select constraint type:",
            constraint_types,
            allow_skip=False
        )
        if not constraint_choice:
            return

        try:
            # Get person name from user
            person1 = self.get_user_input_gui(
                "Select first person:",
                list(self.default_person.keys()),
                allow_skip=False
            )
            if not person1:
                return

            # Initialize new constraint dictionary
            new_constraint = {
                'person1': person1,
                'type': constraint_choice.lower().replace(" ", "_"),
                'description': ''
            }
            
            # Get explanation for constraint
            more_description = self.get_user_input_gui(
                "Enter a strict preference explanation for this constraint"
            )
            if more_description:
                new_constraint['more_description'] = more_description
            
            # Process different types of constraints based on user selection
            if "from specific shop" in constraint_choice:
                # Get shop selection from user
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                new_constraint['shop'] = shop
                
                if "Same" in constraint_choice:
                    # Handle same selection constraint
                    person2 = self.get_user_input_gui(
                        "Select second person:",
                        list(self.default_person.keys()),
                        allow_skip=False
                    )
                    if not person2:
                        return
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have same selection as {person2} in {shop}"
                    
                    # Add appropriate constraint based on shop type
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] == 
                            self.model_state.x[self.default_person[person2]]
                        )
                    elif shop == "Dish Shop" and all(p == "Bobby" for p in [person1, person2]):
                        self.model_state.model.Add(self.model_state.y[0] >= 0)  # Dummy constraint for Bobby's dish
                    else:
                        messagebox.showerror("Error", "Invalid shop selection for these people.")
                        return
                        
                elif "Different" in constraint_choice:
                    # Handle different selection constraint
                    person2 = self.get_user_input_gui(
                        "Select second person:",
                        list(self.default_person.keys()),
                        allow_skip=False
                    )
                    if not person2:
                        return
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have different selection from {person2} in {shop}"
                    
                    # Only valid for Fruit Shop
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] != 
                            self.model_state.x[self.default_person[person2]]
                        )
                    else:
                        messagebox.showerror("Error", "This constraint is only applicable for Fruit Shop.")
                        return
                        
            elif "Must order from" in constraint_choice or "Must not order from" in constraint_choice:
                # Handle must/must not order constraints
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                new_constraint['shop'] = shop
                
                if "Must order from" in constraint_choice:
                    # Process must order constraint
                    new_constraint['type'] = 'must_order'
                    new_constraint['description'] = f"{person1} must order from {shop}"
                    
                    if shop == "Fruit Shop":
                        # Create boolean variables for each possible fruit selection
                        bool_vars = []
                        for item in self.shops[shop].keys():
                            bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')
                            bool_vars.append(bool_var)
                            self.model_state.model.Add(
                                self.model_state.x[self.default_person[person1]] == 
                                self.shops[shop][item]
                            ).OnlyEnforceIf(bool_var)
                        self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one item
                        
                    elif shop == "Dish Shop" and person1 == "Bobby":
                        # Special handling for Bobby's dish selection
                        bool_vars = []
                        for item in self.shops[shop].keys():
                            bool_var = self.model_state.model.NewBoolVar(f'bobby_{item}')
                            bool_vars.append(bool_var)
                            self.model_state.model.Add(
                                self.model_state.y[0] == self.shops[shop][item]
                            ).OnlyEnforceIf(bool_var)
                        self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one dish
                    else:
                        messagebox.showerror("Error", "Only Bobby can order from Dish Shop.")
                        return
                        
                else:  # Must not order from
                    # Process must not order constraint
                    new_constraint['type'] = 'must_not_order'
                    new_constraint['description'] = f"{person1} must not order from {shop}"
                    
                    # Check for conflicts with Bobby's dish shop requirement
                    if person1 == "Bobby" and shop == "Dish Shop":
                        messagebox.showerror("Error", "Cannot restrict Bobby from Dish Shop (default constraint).")
                        return
                        
                    if shop == "Fruit Shop":
                        # Add constraints to prevent selection of any item from the shop
                        for item in self.shops[shop].keys():
                            self.model_state.model.Add(
                                self.model_state.x[self.default_person[person1]] != 
                                self.shops[shop][item]
                            )
            elif "Cannot select" in constraint_choice:
                # Handle restrictions on specific items
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                # Get items to restrict
                items = self.get_user_input_gui(
                    f"Select items from {shop} to restrict:",
                    list(self.shops[shop].keys()),
                    allow_multiple=True
                )
                if not items:
                    messagebox.showerror("Error", "Must select at least one item.")
                    return
                    
                new_constraint['shop'] = shop
                new_constraint['items'] = items
                new_constraint['description'] = f"{person1} cannot select {', '.join(items)} from {shop}"
                
                # Add constraints for each restricted item
                for item in items:
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] != 
                            self.shops[shop][item]
                        )
                    elif shop == "Dish Shop" and person1 == "Bobby":
                        self.model_state.model.Add(
                            self.model_state.y[0] != self.shops[shop][item]
                        )
                    else:
                        messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
                        return
                        
            elif "Must select" in constraint_choice:
                # Handle must-select item constraints
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                # Get allowed items
                items = self.get_user_input_gui(
                    f"Select allowed items from {shop}:",
                    list(self.shops[shop].keys()),
                    allow_multiple=True
                )
                if not items:
                    messagebox.showerror("Error", "Must select at least one item.")
                    return
                    
                new_constraint['shop'] = shop
                new_constraint['items'] = items
                new_constraint['description'] = f"{person1} must select one of {', '.join(items)} from {shop}"
                
                # Create boolean variables for each allowed item
                bool_vars = []
                for item in items:
                    bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')
                    bool_vars.append(bool_var)
                    
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] == 
                            self.shops[shop][item]
                        ).OnlyEnforceIf(bool_var)
                    elif shop == "Dish Shop" and person1 == "Bobby":
                        self.model_state.model.Add(
                            self.model_state.y[0] == self.shops[shop][item]
                        ).OnlyEnforceIf(bool_var)
                    else:
                        messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
                        return
                        
                self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one of the allowed items

            # Check for conflicts with existing constraints
            conflicts = check_constraint_conflicts(new_constraint, self.current_constraints)
            if conflicts:
                # Build conflict message
                conflict_msg = "Found conflicting constraints:\n\n"
                for conflict in conflicts:
                    conflict_msg += conflict['reason'] + "\n"
                    
                    # Handle conflict resolution
                    if conflict.get('is_opposite') or conflict.get('is_duplicate'):
                        if conflict['constraint'].get('is_default', False):
                            # Ask user whether to override default constraint
                            if messagebox.askyesno(
                                "Conflict with Default Constraint",
                                f"This conflicts with default constraint:\n{conflict['constraint']['description']}\n\nDo you want to override it?"
                            ):
                                self.current_constraints.remove(conflict['constraint'])
                                self.write_output(f"Removed conflicting constraint: {conflict['constraint']['description']}\n")
                            else:
                                return
                        else:
                            # Remove non-default conflicting constraint
                            self.current_constraints.remove(conflict['constraint'])
                            self.write_output(f"Removed conflicting constraint: {conflict['constraint']['description']}\n")
                
                # Add new constraint and rebuild model
                self.current_constraints.append(new_constraint)
                
                # Rebuild the entire model with updated constraints
                new_model, new_x, new_y = rebuild_model(
                    self.current_constraints,
                    self.default_person,
                    self.shops
                )
                self.model_state.model = new_model
                self.model_state.x = new_x
                self.model_state.y = new_y
                messagebox.showinfo("Success", "Constraint added and model rebuilt successfully.")
            else:
                # No conflicts, simply add the new constraint
                self.current_constraints.append(new_constraint)
                messagebox.showinfo("Success", f"Constraint added successfully: {new_constraint['description']}")
            
            # Update display
            self.view_constraints()
                
        except Exception as e:
            # Handle any errors during constraint addition
            messagebox.showerror("Error", f"Error adding constraint: {str(e)}")
            if messagebox.askyesno("Retry", "Would you like to try again?"):
                self.show_add_constraint_dialog()

    def show_solution_dialog(self):
        """Dialog for displaying and filtering solutions to the CSP problem"""

        # Define the available options for solution display
        solution_menu_options = [
            "Show all solutions",
            "Show solutions for specific shops",
            "Show solutions with specific items selected"
        ]
        
        # Get user's choice for how to display solutions
        solution_choice = self.get_user_input_gui(
            "Select solution display option:",
            solution_menu_options,
            allow_skip=False  # User must select an option
        )
        if not solution_choice:
            return  # Exit if user cancels
        
        # Create a copy of the model for applying temporary filters
        temp_model = self.model_state.model.Clone()
        
        if solution_choice == "Show solutions for specific shops":
            # Let user select which shops to show in the solution
            self.display_options['shops'] = self.get_user_input_gui(
                "Select shops to show solutions for:",
                list(self.shops.keys()),
            )
            # Let user select which people to show in the solution
            self.display_options['people'] = self.get_user_input_gui(
                "Select people to show solutions for:",
                list(self.default_person.keys()),
            )
            
        elif solution_choice == "Show solutions with specific items selected":
            # Get the shop to filter by
            shop = self.get_user_input_gui(
                "Select shop:",
                list(self.shops.keys())
            )
            if not shop:
                return  # Exit if no shop selected
                
            # Get the items to filter by from the selected shop
            items = self.get_user_input_gui(
                f"Select items to filter solutions for:",
                list(self.shops[shop].keys()),
                allow_multiple=True  # Can select multiple items
            )
            if not items:
                return  # Exit if no items selected
                
            # Get the person whose selections we want to filter
            person_name = self.get_user_input_gui(
                "Select person to filter solutions for:",
                list(self.default_person.keys())
            )
            if not person_name:
                return  # Exit if no person selected
                
            # Add temporary filtering constraints based on the shop type
            if shop == "Fruit Shop":
                bool_vars = []  # List to store boolean variables for each item
                for item in items:
                    # Create a boolean variable for this item selection
                    bool_var = temp_model.NewBoolVar(f'filter_{person_name}_{item}')
                    bool_vars.append(bool_var)
                    # Add constraint that person selects this item when bool_var is true
                    temp_model.Add(
                        self.model_state.x[self.default_person[person_name]] ==
                        self.shops[shop][item]
                    ).OnlyEnforceIf(bool_var)
                temp_model.Add(sum(bool_vars) == 1)  # Ensure exactly one item is selected
            elif shop == "Dish Shop" and person_name == "Bobby":
                bool_vars = []  # List to store boolean variables for each dish
                for item in items:
                    # Create a boolean variable for this dish selection
                    bool_var = temp_model.NewBoolVar(f'filter_bobby_{item}')
                    bool_vars.append(bool_var)
                    # Add constraint that Bobby selects this dish when bool_var is true
                    temp_model.Add(
                        self.model_state.y[0] ==
                        self.shops[shop][item]
                    ).OnlyEnforceIf(bool_var)
                temp_model.Add(sum(bool_vars) == 1)  # Ensure exactly one dish is selected
        
        # Clear previous output and show searching message
        self.clear_output()
        self.write_output("Searching for solutions...\n")
        
        # Create solver instance
        solver = cp_model.CpSolver()
        # Create solution printer to handle and display solutions
        solution_printer = SolutionPrinter(
            self.model_state.x,  # Fruit shop variables
            self.model_state.y,  # Dish shop variables
            self.default_person,  # Person mapping
            self.shops,          # Shop items
            self.display_options,# Display preferences
            self.write_output    # Output function
        )
        
        # Search for all solutions using the temporary model
        status = solver.SearchForAllSolutions(temp_model, solution_printer)
        
        # Display total number of solutions found
        self.write_output(f'\nTotal solutions found: {solution_printer.solution_count()}\n')

        # If no solutions exist, show explanation and current constraints
        if status == cp_model.INFEASIBLE:
            self.write_output('The problem is infeasible - no valid solutions exist with these constraints.\n')
            self.write_output('\nCurrent constraints that might be causing the conflict:\n')
            self.view_constraints()  # Show all constraints to help debug


    def show_edit_description_dialog(self):
        self.clear_output()  # Clear the output area
        self.write_output("Current Constraints:\n")  # Write header
        self.view_constraints()  # Display all current constraints
        
        # Create a list of tuples with indices and constraints, starting from 1
        constraint_list = [(i, c) for i, c in enumerate(self.current_constraints, 1)]
        # Show dialog for user to select which constraint to edit
        selected = self.get_user_input_gui(
            "Select constraint to edit:",
            [f"{i}. {c['description']}" for i, c in constraint_list],  # Format each constraint with number
            allow_skip=True  # Allow user to cancel operation
        )
        
        if selected:  # If user selected a constraint
            idx = int(selected.split('.')[0]) - 1  # Extract index from selection
            constraint = self.current_constraints[idx]  # Get the selected constraint
            
            # Show dialog to get new description, displaying current values
            new_description = self.get_user_input_gui(
                f"Current description: {constraint['description']}\n" +
                (f"Current note: {constraint.get('more_description', '')}\n\n" if constraint.get('more_description') else "\n") +
                "Enter new note (or press Skip to keep current):",
                allow_skip=True  # Allow keeping current description
            )
            
            if new_description:  # If user entered new description
                constraint['more_description'] = new_description  # Update the constraint
                self.write_output("Description updated successfully!\n")  # Confirm update
                self.view_constraints()  # Show updated constraints
            else:
                self.write_output("Description unchanged.\n")  # Inform no changes made


    def view_constraints(self):
        """Display all current constraints, separated into default and custom"""
        self.clear_output()  # Clear the output area
        self.write_output("Current Constraints:\n")  # Write main header
        self.write_output("\nDefault Constraints:\n")  # Write default constraints section header
        
        # First display all default constraints
        for i, constraint in enumerate(self.current_constraints, 1):
            if constraint.get('is_default', False):  # Check if it's a default constraint
                self.write_output(f"{i}. {constraint['description']}\n")  # Write constraint description
                if constraint.get('more_description'):  # If there's additional description
                    self.write_output(f"   Strict Preference: {constraint['more_description']}\n")  # Write it
        
        self.write_output("\nCustom Constraints:\n")  # Write custom constraints section header
        custom_exists = False  # Flag to track if any custom constraints exist
        
        # Then display all custom constraints
        for i, constraint in enumerate(self.current_constraints, 1):
            if not constraint.get('is_default', False):  # Check if it's a custom constraint
                custom_exists = True  # Set flag
                self.write_output(f"{i}. {constraint['description']}\n")  # Write constraint description
                if constraint.get('more_description'):  # If there's additional description
                    self.write_output(f"   Note: {constraint['more_description']}\n")  # Write it
        if not custom_exists:  # If no custom constraints found
            self.write_output("No custom constraints added yet.\n")  # Inform user


    def process_same_selection_constraint(self, person1, person2, shop, new_constraint):
        """Process constraint requiring two people to make the same selection"""
        new_constraint['person2'] = person2  # Add second person to constraint
        new_constraint['description'] = f"{person1} must have same selection as {person2} in {shop}"  # Set description
        
        if shop == "Fruit Shop":  # If constraint is for Fruit Shop
            self.model_state.model.Add(  # Add constraint to model
                self.model_state.x[self.default_person[person1]] == 
                self.model_state.x[self.default_person[person2]]
            )
            return True  # Constraint added successfully
        elif shop == "Dish Shop" and all(p == "Bobby" for p in [person1, person2]):  # If both are Bobby in Dish Shop
            self.model_state.model.Add(self.model_state.y[0] >= 0)  # Add dummy constraint
            return True  # Constraint added successfully
        else:  # Invalid shop/person combination
            messagebox.showerror("Error", "Invalid shop selection for these people.")  # Show error
            return False  # Constraint not added
        
    def process_different_selection_constraint(self, person1, person2, shop, new_constraint):
        """Process constraint requiring two people to make different selections"""
        new_constraint['person2'] = person2  # Set second person in constraint
        new_constraint['description'] = f"{person1} must have different selection from {person2} in {shop}"  # Set description
        
        if shop == "Fruit Shop":  # Only valid for Fruit Shop
            self.model_state.model.Add(  # Add inequality constraint
                self.model_state.x[self.default_person[person1]] != 
                self.model_state.x[self.default_person[person2]]
            )
            return True  # Constraint added successfully
        else:  # Invalid shop specified
            messagebox.showerror("Error", "This constraint is only applicable for Fruit Shop.")
            return False  # Constraint not added

    def process_must_order_constraint(self, person1, shop, new_constraint):
        """Process constraint requiring a person to order from a specific shop"""
        new_constraint['type'] = 'must_order'  # Set constraint type
        new_constraint['description'] = f"{person1} must order from {shop}"  # Set description
        
        if shop == "Fruit Shop":  # Handle Fruit Shop constraints
            bool_vars = []  # List for boolean variables
            for item in self.shops[shop].keys():  # For each item in shop
                bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')  # Create boolean variable
                bool_vars.append(bool_var)  # Add to list
                self.model_state.model.Add(  # Add constraint for this item
                    self.model_state.x[self.default_person[person1]] == 
                    self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)  # Only enforce if this bool is true
            self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one item
            return True
        elif shop == "Dish Shop" and person1 == "Bobby":  # Handle Bobby's dish shop constraints
            bool_vars = []  # List for boolean variables
            for item in self.shops[shop].keys():  # For each dish
                bool_var = self.model_state.model.NewBoolVar(f'bobby_{item}')  # Create boolean variable
                bool_vars.append(bool_var)  # Add to list
                self.model_state.model.Add(  # Add constraint for this dish
                    self.model_state.y[0] == self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)  # Only enforce if this bool is true
            self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one dish
            return True
        else:  # Invalid combination
            messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
            return False

    def process_must_not_order_constraint(self, person1, shop, new_constraint):
        """Process constraint prohibiting a person from ordering from a specific shop"""
        new_constraint['type'] = 'must_not_order'  # Set constraint type
        new_constraint['description'] = f"{person1} must not order from {shop}"  # Set description
        
        if person1 == "Bobby" and shop == "Dish Shop":  # Check for conflict with Bobby's default constraint
            messagebox.showerror("Error", "Cannot restrict Bobby from Dish Shop (default constraint).")
            return False
            
        if shop == "Fruit Shop":  # Handle Fruit Shop restrictions
            for item in self.shops[shop].keys():  # For each item
                self.model_state.model.Add(  # Add inequality constraint
                    self.model_state.x[self.default_person[person1]] != 
                    self.shops[shop][item]
                )
            return True
        return False  # Invalid shop specified

    def process_cannot_select_constraint(self, person1, shop, items, new_constraint):
        """Process constraint prohibiting selection of specific items"""
        new_constraint['shop'] = shop  # Set shop in constraint
        new_constraint['items'] = items  # Set restricted items
        new_constraint['description'] = f"{person1} cannot select {', '.join(items)} from {shop}"  # Set description
        
        for item in items:  # For each restricted item
            if shop == "Fruit Shop":  # Handle Fruit Shop restrictions
                self.model_state.model.Add(  # Add inequality constraint
                    self.model_state.x[self.default_person[person1]] != 
                    self.shops[shop][item]
                )
            elif shop == "Dish Shop" and person1 == "Bobby":  # Handle Bobby's dish restrictions
                self.model_state.model.Add(self.model_state.y[0] != self.shops[shop][item])  # Add inequality constraint
            else:  # Invalid combination
                messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
                return False
        return True

    def process_must_select_constraint(self, person1, shop, items, new_constraint):
        """Process constraint requiring selection from specific items"""
        new_constraint['shop'] = shop  # Set shop in constraint
        new_constraint['items'] = items  # Set allowed items
        new_constraint['description'] = f"{person1} must select one of {', '.join(items)} from {shop}"  # Set description
        
        bool_vars = []  # List for boolean variables
        for item in items:  # For each allowed item
            bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')  # Create boolean variable
            bool_vars.append(bool_var)  # Add to list
            
            if shop == "Fruit Shop":  # Handle Fruit Shop selections
                self.model_state.model.Add(  # Add equality constraint
                    self.model_state.x[self.default_person[person1]] == 
                    self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)  # Only enforce if this bool is true
            elif shop == "Dish Shop" and person1 == "Bobby":  # Handle Bobby's dish selections
                self.model_state.model.Add(  # Add equality constraint
                    self.model_state.y[0] == self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)  # Only enforce if this bool is true
            else:  # Invalid combination
                messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
                return False
        
        self.model_state.model.Add(sum(bool_vars) == 1)  # Must select exactly one item
        return True

    def rebuild_current_model(self):
        """Rebuild the entire model with current constraints"""
        new_model, new_x, new_y = rebuild_model(  # Call rebuild function
            self.current_constraints,  # Pass current constraints
            self.default_person,      # Pass person mapping
            self.shops               # Pass shop data
        )
        self.model_state.model = new_model  # Update model
        self.model_state.x = new_x  # Update fruit shop variables
        self.model_state.y = new_y  # Update dish shop variables
        self.write_output("Model rebuilt with updated constraints.\n")  # Confirm rebuild

    def confirm_action(self, title, message):
        """Show yes/no dialog to confirm an action"""
        return messagebox.askyesno(title, message)  # Return user's choice

    def show_error(self, title, message):
        """Show error message dialog"""
        messagebox.showerror(title, message)  # Display error message

    def show_info(self, title, message):
        """Show information message dialog"""
        messagebox.showinfo(title, message)  # Display info message


# Main execution code
def main():
    """Main function to initialize and run the CSP Solver application"""
    root = tk.Tk()  # Create the main application window
    root.title("Food CSP Solver")  # Set window title
    
    # Set up styles
    style = ttk.Style()  # Create style object for ttk widgets
    style.configure('Action.TButton', padding=5)  # Configure custom button style with padding
    
    # Create and run application
    try:
        app = CSPSolverGUI(root)  # Initialize main application class
        root.mainloop()  # Start the Tkinter event loop
    except Exception as e:  # Catch any errors during execution
        messagebox.showerror(  # Show error dialog
            "Error",
            f"An error occurred: {str(e)}\nPlease restart the application."  # Display error message with restart instruction
        )

if __name__ == "__main__":  # Only run if this is the main script
    main()  # Call the main function to start the application

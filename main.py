import sys
from io import StringIO
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ortools.sat.python import cp_model

class ModelState:
    def __init__(self, model, x, y):
        self.model = model
        self.x = x
        self.y = y


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, x, y, person, shops, display_options, output_callback):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._x = x
        self._y = y
        self._person = person
        self._shops = shops
        self._display_options = display_options
        self._solution_count = 0
        self._output_callback = output_callback  # Function to write to GUI

    def print_shop_header(self, shop_type, items):
        header = f"\n{shop_type}\n"
        header += "Person    | " + " | ".join(item.ljust(8) for item in items) + "\n"
        header += "-" * len(header) + "\n"
        self._output_callback(header)

    def on_solution_callback(self):
        # Same logic but use output_callback instead of print
        self._solution_count += 1
        self._output_callback(f'\nSolution {self._solution_count}:\n')
        
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
                        
                        self._output_callback(f"{person_name}| {' | '.join(selections)}\n")

    def solution_count(self):
        return self._solution_count

class GUIInputDialog:
    def __init__(self, parent, prompt, options=None, allow_skip=True, allow_multiple=False):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Input Required")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.result = None
        self.options = options
        self.allow_multiple = allow_multiple
        
        # Create dialog content
        ttk.Label(self.dialog, text=prompt, wraplength=350).pack(pady=5)
        
        if options:
            if allow_multiple:
                self.vars = []
                frame = ttk.Frame(self.dialog)
                frame.pack(fill='both', expand=True, padx=5, pady=5)
                canvas = tk.Canvas(frame)
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                for opt in options:
                    var = tk.BooleanVar()
                    self.vars.append(var)
                    ttk.Checkbutton(scrollable_frame, text=opt, variable=var).pack(pady=2)
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
            else:
                self.var = tk.StringVar()
                for opt in options:
                    ttk.Radiobutton(self.dialog, text=opt, 
                                  variable=self.var, value=opt).pack(pady=2)
        else:
            self.entry = ttk.Entry(self.dialog, width=50)
            self.entry.pack(pady=5)
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side='bottom', pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side='left', padx=5)
        if allow_skip:
            ttk.Button(button_frame, text="Skip", command=self.on_skip).pack(side='left', padx=5)
        
        # Center the dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def on_ok(self):
        if self.options:
            if self.allow_multiple:
                self.result = [opt for i, opt in enumerate(self.options) 
                             if self.vars[i].get()]
            else:
                self.result = self.var.get()
        else:
            self.result = self.entry.get()
        self.dialog.destroy()

    def on_skip(self):
        self.result = [] if self.allow_multiple else None
        self.dialog.destroy()



class CSPSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Food CSP Solver")
        self.root.geometry("1000x800")
        
        # Initialize model state and data
        self.initialize_data()
        
        # Create main container with padding
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Create GUI elements
        self.create_output_area()
        self.create_buttons()
        
        # Initial welcome message
        self.write_output("Welcome to the Food Constraint Satisfaction Problem (CSP) Solver!\n")
        self.write_output("\nDefault constraints have been set up.\n")
        self.view_constraints()

    def initialize_data(self):
        # Initialize all the data structures and models
        self.default_person = dict(Adam=0, Bobby=1, Cathy=2, Dean=3)
        self.shops = {
            "Fruit Shop": dict(Papaya=0, Quenepa=1, Rambutan=2, Salak=3),
            "Dish Shop": dict(Pasta=0, Risotto=1)
        }
        
        # Create initial model
        model = cp_model.CpModel()
        x = [model.NewIntVar(0, len(self.shops["Fruit Shop"]) - 1, f'x_{i}') 
             for i in range(len(self.default_person))]
        y = [model.NewIntVar(0, len(self.shops["Dish Shop"]) - 1, 'bobby_dish')]
        
        # Set up default constraints
        self.current_constraints = create_default_constraints(model, x, y, 
                                                           self.default_person, self.shops)
        self.model_state = ModelState(model, x, y)
        
        # Add Bobby's dish constraint
        bobby_pasta = self.model_state.model.NewBoolVar('bobby_pasta')
        bobby_risotto = self.model_state.model.NewBoolVar('bobby_risotto')
        self.model_state.model.Add(self.model_state.y[0] == 
                                 self.shops["Dish Shop"]["Pasta"]).OnlyEnforceIf(bobby_pasta)
        self.model_state.model.Add(self.model_state.y[0] == 
                                 self.shops["Dish Shop"]["Risotto"]).OnlyEnforceIf(bobby_risotto)
        self.model_state.model.Add(bobby_pasta + bobby_risotto == 1)
        
        self.current_constraints.append({
            'type': 'must_order',
            'person1': 'Bobby',
            'shop': 'Dish Shop',
            'description': 'Bobby must select one of Pasta, Risotto from Dish Shop',
            'more_description': 'Bobby will only order pasta or risotto',
            'is_default': True
        })
        
        self.display_options = {
            'shops': ["Fruit Shop", "Dish Shop"],
            'people': ["Adam", "Bobby", "Cathy", "Dean"]
        }

    def create_output_area(self):
        # Create output frame with label
        output_frame = ttk.LabelFrame(self.main_container, text="Output", padding="5")
        output_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        
        # Create output text area with scrollbar
        self.output_area = scrolledtext.ScrolledText(
            output_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=30,
            font=('Courier', 10)
        )
        self.output_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.output_area.config(state='disabled')

    def create_buttons(self):
        # Create button frame
        button_frame = ttk.Frame(self.main_container, padding="5")
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Create buttons
        buttons = [
            ("Add Constraint", self.show_add_constraint_dialog),
            ("View Constraints", self.view_constraints),
            ("Find Solutions", self.show_solution_dialog),
            ("Edit Descriptions", self.show_edit_description_dialog),
            ("Exit", self.root.quit)
        ]
        
        for i, (text, command) in enumerate(buttons):
            btn = ttk.Button(button_frame, text=text, command=command, style='Action.TButton')
            btn.grid(row=0, column=i, padx=5)
            button_frame.grid_columnconfigure(i, weight=1)

    def write_output(self, text):
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text)
        self.output_area.config(state='disabled')
        self.output_area.see(tk.END)

    def clear_output(self):
        self.output_area.config(state='normal')
        self.output_area.delete(1.0, tk.END)
        self.output_area.config(state='disabled')

    def get_user_input_gui(self, prompt, options=None, allow_skip=True, allow_multiple=False):
        """GUI version of get_user_input"""
        dialog = GUIInputDialog(self.root, prompt, options, allow_skip, allow_multiple)
        self.root.wait_window(dialog.dialog)
        return dialog.result

    def show_add_constraint_dialog(self):
        constraint_types = [
            "Same selection from specific shop",
            "Different selection from specific shop",
            "Must order from specific shop",
            "Must not order from specific shop",
            "Cannot select specific items",
            "Must select specific items"
        ]
        
        constraint_choice = self.get_user_input_gui(
            "Select constraint type:",
            constraint_types,
            allow_skip=False
        )
        if not constraint_choice:
            return

        try:
            person1 = self.get_user_input_gui(
                "Select first person:",
                list(self.default_person.keys()),
                allow_skip=False
            )
            if not person1:
                return

            new_constraint = {
                'person1': person1,
                'type': constraint_choice.lower().replace(" ", "_"),
                'description': ''
            }
            
            more_description = self.get_user_input_gui(
                "Enter a strict preference explanation for this constraint"
            )
            if more_description:
                new_constraint['more_description'] = more_description

            if "from specific shop" in constraint_choice:
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                new_constraint['shop'] = shop
                
                if "Same" in constraint_choice:
                    person2 = self.get_user_input_gui(
                        "Select second person:",
                        list(self.default_person.keys()),
                        allow_skip=False
                    )
                    if not person2:
                        return
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have same selection as {person2} in {shop}"
                    
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] == 
                            self.model_state.x[self.default_person[person2]]
                        )
                    elif shop == "Dish Shop" and all(p == "Bobby" for p in [person1, person2]):
                        self.model_state.model.Add(self.model_state.y[0] >= 0)
                    else:
                        messagebox.showerror("Error", "Invalid shop selection for these people.")
                        return
                        
                elif "Different" in constraint_choice:
                    person2 = self.get_user_input_gui(
                        "Select second person:",
                        list(self.default_person.keys()),
                        allow_skip=False
                    )
                    if not person2:
                        return
                        
                    new_constraint['person2'] = person2
                    new_constraint['description'] = f"{person1} must have different selection from {person2} in {shop}"
                    
                    if shop == "Fruit Shop":
                        self.model_state.model.Add(
                            self.model_state.x[self.default_person[person1]] != 
                            self.model_state.x[self.default_person[person2]]
                        )
                    else:
                        messagebox.showerror("Error", "This constraint is only applicable for Fruit Shop.")
                        return
                        
            elif "Must order from" in constraint_choice or "Must not order from" in constraint_choice:
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
                new_constraint['shop'] = shop
                
                if "Must order from" in constraint_choice:
                    new_constraint['type'] = 'must_order'
                    new_constraint['description'] = f"{person1} must order from {shop}"
                    
                    if shop == "Fruit Shop":
                        bool_vars = []
                        for item in self.shops[shop].keys():
                            bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')
                            bool_vars.append(bool_var)
                            self.model_state.model.Add(
                                self.model_state.x[self.default_person[person1]] == 
                                self.shops[shop][item]
                            ).OnlyEnforceIf(bool_var)
                        self.model_state.model.Add(sum(bool_vars) == 1)
                        
                    elif shop == "Dish Shop":
                        if person1 == "Bobby":
                            bool_vars = []
                            for item in self.shops[shop].keys():
                                bool_var = self.model_state.model.NewBoolVar(f'bobby_{item}')
                                bool_vars.append(bool_var)
                                self.model_state.model.Add(
                                    self.model_state.y[0] == self.shops[shop][item]
                                ).OnlyEnforceIf(bool_var)
                            self.model_state.model.Add(sum(bool_vars) == 1)
                        else:
                            messagebox.showerror("Error", "Only Bobby can order from Dish Shop.")
                            return
                        
                else:  # Must not order from
                    new_constraint['type'] = 'must_not_order'
                    new_constraint['description'] = f"{person1} must not order from {shop}"
                    
                    if person1 == "Bobby" and shop == "Dish Shop":
                        messagebox.showerror("Error", "Cannot restrict Bobby from Dish Shop (default constraint).")
                        return
                        
                    if shop == "Fruit Shop":
                        for item in self.shops[shop].keys():
                            self.model_state.model.Add(
                                self.model_state.x[self.default_person[person1]] != 
                                self.shops[shop][item]
                            )
                    
            elif "Cannot select" in constraint_choice:
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
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
                shop = self.get_user_input_gui(
                    "Select shop:",
                    list(self.shops.keys()),
                    allow_skip=False
                )
                if not shop:
                    return
                    
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
                        
                self.model_state.model.Add(sum(bool_vars) == 1)

            # Check for conflicts
            conflicts = check_constraint_conflicts(new_constraint, self.current_constraints)
            if conflicts:
                conflict_msg = "Found conflicting constraints:\n\n"
                for conflict in conflicts:
                    conflict_msg += conflict['reason'] + "\n"
                    
                    if conflict.get('is_opposite') or conflict.get('is_duplicate'):
                        if conflict['constraint'].get('is_default', False):
                            if messagebox.askyesno(
                                "Conflict with Default Constraint",
                                f"This conflicts with default constraint:\n{conflict['constraint']['description']}\n\nDo you want to override it?"
                            ):
                                self.current_constraints.remove(conflict['constraint'])
                                self.write_output(f"Removed conflicting constraint: {conflict['constraint']['description']}\n")
                            else:
                                return
                        else:
                            self.current_constraints.remove(conflict['constraint'])
                            self.write_output(f"Removed conflicting constraint: {conflict['constraint']['description']}\n")
                
                self.current_constraints.append(new_constraint)
                
                # Rebuild the model
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
                self.current_constraints.append(new_constraint)
                messagebox.showinfo("Success", f"Constraint added successfully: {new_constraint['description']}")
            
            self.view_constraints()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error adding constraint: {str(e)}")
            if messagebox.askyesno("Retry", "Would you like to try again?"):
                self.show_add_constraint_dialog()

    def show_solution_dialog(self):
        solution_menu_options = [
            "Show all solutions",
            "Show solutions for specific shops",
            "Show solutions with specific items selected"
        ]
        
        solution_choice = self.get_user_input_gui(
            "Select solution display option:",
            solution_menu_options,
            allow_skip=False
        )
        if not solution_choice:
            return
            
        temp_model = self.model_state.model.Clone()
        
        if solution_choice == "Show solutions for specific shops":
            self.display_options['shops'] = self.get_user_input_gui(
                "Select shops to show solutions for:",
                list(self.shops.keys()),
                allow_multiple=True
            )
            self.display_options['people'] = self.get_user_input_gui(
                "Select people to show solutions for:",
                list(self.default_person.keys()),
                allow_multiple=True
            )
            
        elif solution_choice == "Show solutions with specific items selected":
            shop = self.get_user_input_gui(
                "Select shop:",
                list(self.shops.keys())
            )
            if not shop:
                return
                
            items = self.get_user_input_gui(
                f"Select items to filter solutions for:",
                list(self.shops[shop].keys()),
                allow_multiple=True
            )
            if not items:
                return
                
            person_name = self.get_user_input_gui(
                "Select person to filter solutions for:",
                list(self.default_person.keys())
            )
            if not person_name:
                return
                
            # Add temporary constraint for filtering
            if shop == "Fruit Shop":
                bool_vars = []
                for item in items:
                    bool_var = temp_model.NewBoolVar(f'filter_{person_name}_{item}')
                    bool_vars.append(bool_var)
                    temp_model.Add(
                        self.model_state.x[self.default_person[person_name]] ==
                        self.shops[shop][item]
                    ).OnlyEnforceIf(bool_var)
                temp_model.Add(sum(bool_vars) == 1)
            elif shop == "Dish Shop" and person_name == "Bobby":
                bool_vars = []
                for item in items:
                    bool_var = temp_model.NewBoolVar(f'filter_bobby_{item}')
                    bool_vars.append(bool_var)
                    temp_model.Add(
                        self.model_state.y[0] ==
                        self.shops[shop][item]
                    ).OnlyEnforceIf(bool_var)
                temp_model.Add(sum(bool_vars) == 1)
        
        self.clear_output()
        self.write_output("Searching for solutions...\n")
        
        solver = cp_model.CpSolver()
        solution_printer = SolutionPrinter(
            self.model_state.x,
            self.model_state.y,
            self.default_person,
            self.shops,
            self.display_options,
            self.write_output
        )
        
        status = solver.SearchForAllSolutions(temp_model, solution_printer)
        
        self.write_output(f'\nTotal solutions found: {solution_printer.solution_count()}\n')
        if status == cp_model.INFEASIBLE:
            self.write_output('The problem is infeasible - no valid solutions exist with these constraints.\n')
            self.write_output('\nCurrent constraints that might be causing the conflict:\n')
            self.view_constraints()

    def show_edit_description_dialog(self):
        self.clear_output()
        self.write_output("Current Constraints:\n")
        self.view_constraints()
        
        constraint_list = [(i, c) for i, c in enumerate(self.current_constraints, 1)]
        selected = self.get_user_input_gui(
            "Select constraint to edit:",
            [f"{i}. {c['description']}" for i, c in constraint_list],
            allow_skip=True
        )
        
        if selected:
            idx = int(selected.split('.')[0]) - 1
            constraint = self.current_constraints[idx]
            
            new_description = self.get_user_input_gui(
                f"Current description: {constraint['description']}\n" +
                (f"Current note: {constraint.get('more_description', '')}\n\n" if constraint.get('more_description') else "\n") +
                "Enter new note (or press Skip to keep current):",
                allow_skip=True
            )
            
            if new_description:
                constraint['more_description'] = new_description
                self.write_output("Description updated successfully!\n")
                self.view_constraints()
            else:
                self.write_output("Description unchanged.\n")

    def view_constraints(self):
        self.clear_output()
        self.write_output("Current Constraints:\n")
        self.write_output("\nDefault Constraints:\n")
        for i, constraint in enumerate(self.current_constraints, 1):
            if constraint.get('is_default', False):
                self.write_output(f"{i}. {constraint['description']}\n")
                if constraint.get('more_description'):
                    self.write_output(f"   Strict Preference: {constraint['more_description']}\n")
        
        self.write_output("\nCustom Constraints:\n")
        custom_exists = False
        for i, constraint in enumerate(self.current_constraints, 1):
            if not constraint.get('is_default', False):
                custom_exists = True
                self.write_output(f"{i}. {constraint['description']}\n")
                if constraint.get('more_description'):
                    self.write_output(f"   Note: {constraint['more_description']}\n")
        if not custom_exists:
            self.write_output("No custom constraints added yet.\n")


    def process_same_selection_constraint(self, person1, person2, shop, new_constraint):
        new_constraint['person2'] = person2
        new_constraint['description'] = f"{person1} must have same selection as {person2} in {shop}"
        
        if shop == "Fruit Shop":
            self.model_state.model.Add(
                self.model_state.x[self.default_person[person1]] == 
                self.model_state.x[self.default_person[person2]]
            )
            return True
        elif shop == "Dish Shop" and all(p == "Bobby" for p in [person1, person2]):
            self.model_state.model.Add(self.model_state.y[0] >= 0)
            return True
        else:
            messagebox.showerror("Error", "Invalid shop selection for these people.")
            return False

    def process_different_selection_constraint(self, person1, person2, shop, new_constraint):
        new_constraint['person2'] = person2
        new_constraint['description'] = f"{person1} must have different selection from {person2} in {shop}"
        
        if shop == "Fruit Shop":
            self.model_state.model.Add(
                self.model_state.x[self.default_person[person1]] != 
                self.model_state.x[self.default_person[person2]]
            )
            return True
        else:
            messagebox.showerror("Error", "This constraint is only applicable for Fruit Shop.")
            return False

    def process_must_order_constraint(self, person1, shop, new_constraint):
        new_constraint['type'] = 'must_order'
        new_constraint['description'] = f"{person1} must order from {shop}"
        
        if shop == "Fruit Shop":
            bool_vars = []
            for item in self.shops[shop].keys():
                bool_var = self.model_state.model.NewBoolVar(f'{person1}_{item}')
                bool_vars.append(bool_var)
                self.model_state.model.Add(
                    self.model_state.x[self.default_person[person1]] == 
                    self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)
            self.model_state.model.Add(sum(bool_vars) == 1)
            return True
        elif shop == "Dish Shop" and person1 == "Bobby":
            bool_vars = []
            for item in self.shops[shop].keys():
                bool_var = self.model_state.model.NewBoolVar(f'bobby_{item}')
                bool_vars.append(bool_var)
                self.model_state.model.Add(
                    self.model_state.y[0] == self.shops[shop][item]
                ).OnlyEnforceIf(bool_var)
            self.model_state.model.Add(sum(bool_vars) == 1)
            return True
        else:
            messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
            return False

    def process_must_not_order_constraint(self, person1, shop, new_constraint):
        new_constraint['type'] = 'must_not_order'
        new_constraint['description'] = f"{person1} must not order from {shop}"
        
        if person1 == "Bobby" and shop == "Dish Shop":
            messagebox.showerror("Error", "Cannot restrict Bobby from Dish Shop (default constraint).")
            return False
            
        if shop == "Fruit Shop":
            for item in self.shops[shop].keys():
                self.model_state.model.Add(
                    self.model_state.x[self.default_person[person1]] != 
                    self.shops[shop][item]
                )
            return True
        return False

    def process_cannot_select_constraint(self, person1, shop, items, new_constraint):
        new_constraint['shop'] = shop
        new_constraint['items'] = items
        new_constraint['description'] = f"{person1} cannot select {', '.join(items)} from {shop}"
        
        for item in items:
            if shop == "Fruit Shop":
                self.model_state.model.Add(
                    self.model_state.x[self.default_person[person1]] != 
                    self.shops[shop][item]
                )
            elif shop == "Dish Shop" and person1 == "Bobby":
                self.model_state.model.Add(self.model_state.y[0] != self.shops[shop][item])
            else:
                messagebox.showerror("Error", "Invalid shop/person combination for this constraint.")
                return False
        return True

    def process_must_select_constraint(self, person1, shop, items, new_constraint):
        new_constraint['shop'] = shop
        new_constraint['items'] = items
        new_constraint['description'] = f"{person1} must select one of {', '.join(items)} from {shop}"
        
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
                return False
        
        self.model_state.model.Add(sum(bool_vars) == 1)
        return True

    # Add a method to handle the rebuild process
    def rebuild_current_model(self):
        new_model, new_x, new_y = rebuild_model(
            self.current_constraints,
            self.default_person,
            self.shops
        )
        self.model_state.model = new_model
        self.model_state.x = new_x
        self.model_state.y = new_y
        self.write_output("Model rebuilt with updated constraints.\n")

    def confirm_action(self, title, message):
        return messagebox.askyesno(title, message)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        messagebox.showinfo(title, message)

# Main execution code
def main():
    root = tk.Tk()
    root.title("Food CSP Solver")
    
    # Set up styles
    style = ttk.Style()
    style.configure('Action.TButton', padding=5)
    
    # Create and run application
    try:
        app = CSPSolverGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"An error occurred: {str(e)}\nPlease restart the application."
        )

if __name__ == "__main__":
    main()

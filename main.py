from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, x, y, person, fruit, dishes):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._x = x  # for fruits
        self._y = y  # for Bobby's dish
        self._person = person
        self._fruit = fruit
        self._dishes = dishes
        self._solution_count = 0

    def print_shop_header(self, shop_type, items):
        print(f"\n{shop_type} Shop")
        header = "Person    | " + " | ".join(item.ljust(8) for item in items)
        print(header)
        print("-" * len(header))

    def on_solution_callback(self):
        self._solution_count += 1
        print(f'\nSolution {self._solution_count}:')
        
        # Print Fruit Shop Table
        self.print_shop_header("Fruit", list(self._fruit.keys()))
        for n, var in enumerate(self._x):
            person_name = list(self._person)[n].ljust(9)
            fruit_val = self.Value(var)
            
            # Initialize all fruits as N/A
            selections = ["N/A".ljust(8) for _ in range(len(self._fruit))]
            
            # Set the selected fruit
            selections[fruit_val] = "Selected".ljust(8)
            
            # Print the row
            print(f"{person_name}| {' | '.join(selections)}")

        # Print Dish Shop Table
        self.print_shop_header("Dish", list(self._dishes.keys()))
        for n in range(len(self._person)):
            person_name = list(self._person)[n].ljust(9)
            
            # Initialize all dishes as N/A
            selections = ["N/A".ljust(8) for _ in range(len(self._dishes))]
            
            # If it's Bobby, show his dish selection
            if n == self._person['Bobby']:
                dish_val = self.Value(self._y[0])
                selections[dish_val] = "Selected".ljust(8)
            
            # Print the row
            print(f"{person_name}| {' | '.join(selections)}")

    def solution_count(self):
        return self._solution_count


def solve_fruit_assignment():
    model = cp_model.CpModel()
    person = dict(Adam=0,
                  Bobby=1,
                  Cathy=2,
                  Dean=3)
    fruit = dict(Papaya=0,
                 Quenepa=1,
                 Rambutan=2,
                 Salak=3)
    dishes = dict(Pasta=0,
                 Risotto=1)

    # Variables for fruits (for everyone including Bobby)
    x = [model.NewIntVar(0, len(fruit) - 1, f'x_{i}') for i in range(len(person))]
    
    # Additional variable for Bobby's dish selection
    y = [model.NewIntVar(0, len(dishes) - 1, 'bobby_dish')]

    # Constraint: Cathy will not pick Salak
    model.Add(x[person['Cathy']] != fruit['Salak'])

    # Constraint: Adam and Bobby must have different fruits
    model.Add(x[person['Adam']] != x[person['Bobby']])

    # Constraint: Bobby's dish selection (must pick either Pasta or Risotto)
    bobby_pasta = model.NewBoolVar('bobby_pasta')
    bobby_risotto = model.NewBoolVar('bobby_risotto')

    # Link the boolean variables to Bobby's dish choices
    model.Add(y[0] == dishes['Pasta']).OnlyEnforceIf(bobby_pasta)
    model.Add(y[0] == dishes['Risotto']).OnlyEnforceIf(bobby_risotto)

    # Ensure Bobby picks exactly one dish
    model.Add(bobby_pasta + bobby_risotto == 1)

    # Constraint: Adam and Cathy must have the same fruit (best friends exception)
    model.Add(x[person['Adam']] == x[person['Cathy']])

    # Constraint: Cathy must have different fruit from Bobby and Dean
    model.Add(x[person['Cathy']] != x[person['Bobby']])
    model.Add(x[person['Cathy']] != x[person['Dean']])

    # Constraint: Dean dislikes Quenepa
    model.Add(x[person['Dean']] != fruit['Quenepa'])

    # Create solver and solution printer
    solver = cp_model.CpSolver()
    solution_printer = SolutionPrinter(x, y, person, fruit, dishes)

    # Search for all solutions
    status = solver.SearchForAllSolutions(model, solution_printer)

    # Print final count
    print(f'\nTotal solutions found: {solution_printer.solution_count()}')

    if status == cp_model.INFEASIBLE:
        print('The problem is infeasible')


if __name__ == '__main__':
    solve_fruit_assignment()
    
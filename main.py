from ortools.sat.python import cp_model


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, x, person, fruit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._x = x
        self._person = person
        self._fruit = fruit
        self._solution_count = 0

    def on_solution_callback(self):
        self._solution_count += 1
        print(f'\nSolution {self._solution_count}:')
        for n, var in enumerate(self._x):
            print(f'Person: {list(self._person)[n]}: Fruit: {list(self._fruit)[self.Value(var)]}')

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

    # Variables
    x = [model.NewIntVar(0, len(fruit) - 1, f'x_{i}') for i in range(len(person))]

    # Constraint: Cathy will not pick Salak
    model.Add(x[person['Cathy']] != fruit['Salak'])

    # Constraint: Adam and Bobby must have different fruits
    model.Add(x[person['Adam']] != x[person['Bobby']])

    # Constraint: Bobby will only pick Papaya or Rambutan
    bobby_papaya = model.NewBoolVar('bobby_papaya')
    bobby_rambutan = model.NewBoolVar('bobby_rambutan')

    # Link the boolean variables to Bobby's choices
    model.Add(x[person['Bobby']] == fruit['Papaya']).OnlyEnforceIf(bobby_papaya)
    model.Add(x[person['Bobby']] == fruit['Rambutan']).OnlyEnforceIf(bobby_rambutan)

    # Ensure Bobby picks exactly one of these options
    model.Add(bobby_papaya + bobby_rambutan == 1)

    # Constraint: Adam and Cathy must have the same fruit (best friends exception)
    model.Add(x[person['Adam']] == x[person['Cathy']])

    # Constraint: Cathy must have different fruit from Bobby and Dean
    # (Note: This combined with the above means Adam will also have different fruit from Bobby and Dean)
    model.Add(x[person['Cathy']] != x[person['Bobby']])
    model.Add(x[person['Cathy']] != x[person['Dean']])

    # Constraint: Dean dislikes Quenepa
    model.Add(x[person['Dean']] != fruit['Quenepa'])

    # Create solver and solution printer
    solver = cp_model.CpSolver()
    solution_printer = SolutionPrinter(x, person, fruit)

    # Search for all solutions
    status = solver.SearchForAllSolutions(model, solution_printer)

    # Print final count
    print(f'\nTotal solutions found: {solution_printer.solution_count()}')

    if status == cp_model.INFEASIBLE:
        print('The problem is infeasible')


if __name__ == '__main__':
    solve_fruit_assignment()

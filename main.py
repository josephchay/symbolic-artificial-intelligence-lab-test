from ortools.sat.python import cp_model

model = cp_model.CpModel()
person = dict(Adam=0,
              Bobby=1,
              Cathy=2,
              Dean=3)
fruit = dict(Papaya=0,
             Quenepa=1,
             Rambutan=2,
             Salak=3)

x = [model.NewIntVar(0, len(fruit), f'x_{i}') for i in range(len(person))]

# Constraint C ≠ S
model.Add(x[person['Cathy']] != fruit['Salak'])

# Constraint A ≠ B
model.Add(x[person['Adam']] != x[person['Bobby']])

# Constraint B ∈ {P,R}
flags = [model.NewBoolVar(f'flag{i}') for i in range(4)]
for i in range(len(person)):
    if (i == fruit['Papaya']) | (i == fruit['Rambutan']):
        model.Add(x[i] == i).OnlyEnforceIf(flags[i])
        model.Add(x[i] != i).OnlyEnforceIf(flags[i].Not())

# Constraint C ∉ {B, D}
model.Add(x[person['Cathy']] != x[person['Bobby']])
model.Add(x[person['Cathy']] != x[person['Dean']])

# Constraint D ≠ Q
model.Add(x[person['Dean']] != fruit['Quenepa'])

solver = cp_model.CpSolver()
status = solver.Solve(model)
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    for n, dval in enumerate(x):
        print(f'Person: {list(person)[n]}: Fruit: {list(fruit)[solver.Value(dval)]}')
else:
    print('unsat')

# Symbolic Artificial Intelligence - Lab Test

This repository contains the code for the lab test according to prescribed documents and requirements for 
the module Symbolic Artificial Intelligence at the University of Nottingham Malaysia campus.

---

## Guide

Read the CHANGELOG.md for a better understanding of the log tracking all code enhancements, new constraints additions, and extraordinary features added.

It provides a strong guide accompanied with the git commit history on which feature was implemented in which design history.

The code was purposefully structure in a clean and well factored way with usage of necessary Object-Oriented Concepts (OOP) as well as reusable generic functions. This project was purposefully organized in the way which prioritize both code structure and prevention of technical debt while yet maintaining the potential readbility for developers and users of this codebase.

## Installation and Execution

### Install all of the required dependencies.

- Packages such as `sys` and `os` do not required to be manually installed as they already come with the Python package.

```bash
pip install -r requirements.txt
```

### Code Execution

- Execute the `main.py` file and begin to use the system with a well rounded and guided UI for wholesome UX experience, present with all graceful error handlings and proper exitable loops. 

```bash
python main.py
```

## Usage

### Home Menu

![image](https://github.com/user-attachments/assets/8863e58d-f05b-470d-9d92-64fee6e19fd0)

As the program first executes, you will be first brought to the Main Menu Home Page. The Main Menu consist of the main output panel which will first show all the `current constraints` that are set by default as per the requirements. Below this output panel stands a total of 5 different action buttons. All which have multi unique purposes within each of them.

![image](https://github.com/user-attachments/assets/f2f61567-4767-4ad9-9f3c-0d7afd9741db)

#### Constraint Addition

The first button `Add Constraint` allows the user to add different constraint types based on his / her choice as laid out in the input panel of a total of 6 different options. The selected option will then further lead to their respective needed further detail selection.

![image](https://github.com/user-attachments/assets/8a0af5cc-1b49-4149-85c8-44af0a86842f)

![image](https://github.com/user-attachments/assets/c386949e-e913-4144-a8a8-e37ae526f693)

> For instance, the initial selection for `Different selection from specific shop` then leads the user to then having to select the first and second person as well as the shop type. Moreover, the user also has the freedom to insert both First Order Logic and Propositional Logic for the new constraint as seen in the image directly above. This is likewise for other options.

The newly added constraint will then be validated with proper error handling to check whether if the new introduced one is conflicting with any of the current existing one. If it is, then the user will be prompted for further action confirmation. Whereby upon the `Yes` button, the old constraint will then be updated with the new one. `No` will then discard the new change.

**Database for Constraints** The newly updated dictionary of constraints will also be appended to the `constraints_db.txt` where this will allow the user to not have the need to constantly update the list upon each login. The data will be persistent instead.

#### View Constraints

This button allows the user to view the current constraints that is always up to date, consisting of two categories:

1. Default Constraints
2. Custom Constraints

The default category holds the initial dictionary as well as any newly removed pertaining to the modification of the user.

The custom category holds all the newly added dictionary of constraints that have been introduced by the user.

#### Find Solution

![image](https://github.com/user-attachments/assets/274d53a7-1c97-4856-92a7-9af0f060301c)

This button contains 3 other buttons:
1. Show all solutions that are feasible and possible
2. Filter and show solutions based on the specific selected shop type
3. Filter and show the solutions based on the specific items that have been selected.

**Find all solutions**

![image](https://github.com/user-attachments/assets/39c60e13-df95-41e3-84ff-41bc80e5924b)

As seen in the image above, this is the image example of all the possible solutions by the current constraints that have been set prior. It shows all the total number of solutions found as well as each of the possible combination for each of the person, item, and shop type as per set by the constraints.

**Filter and find solutions based on selected shops and / or persons**

![image](https://github.com/user-attachments/assets/df73405f-809a-4f25-82e8-aaaf7b2b6c87)


![image](https://github.com/user-attachments/assets/54ea74bc-6ca6-4485-9c02-ba97ec5ac37a)

The above is for the second option mainly to show all the solutions based on the selected shop to include in the table. The persons are also allowed to be selected or skipped as per the desire of the user.

> For instance, as shown in the sample image above, That's the possible results for the fruit shop and under the person Cathy.

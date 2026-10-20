#!/usr/bin/env python3
"""Apply manual OCR corrections to all 30 scraped quiz files."""

import json
from pathlib import Path

CORRECTIONS = {
    # Quiz ID -> {question_number: corrected_text}
    "e5eu": {  # Names of 3D shapes
        1: "Which of the following is a correct name of this shape?\n\n[Cube] [Rectangle] [Pyramid] [Cuboid]",
        2: "Which of the following shapes is a triangular prism?\n\n[A] [B] [C] [D]",
        3: "Which of the following shapes is not a prism?\n\n[A - cube] [B - pyramid] [C - triangular prism] [D - octagonal prism]",
        4: "Which of the following is a correct name of this shape?\n\n[Square-based pyramid] [Triangular prism] [Cone] [Triangular-based pyramid]",
        5: "Which of the following shapes is a cylinder?\n\n[A - rectangle] [B - cylinder] [C - sphere] [D - hemisphere]",
    },
    "e900": {  # Estimation 2
        1: "Which of the following is the most sensible calculation to estimate the answer to: 23 × 199\n\n[20 × 200] [30 × 190] [20 × 100] [0 × 200]",
        2: "Which of the following is the most sensible calculation to estimate the answer to: 17 / 0.483\n\n[10 / 1] [20 / 0.5] [17 / 0.5] [20 / 1]",
        3: "Julie wants to estimate the answer to this calculation by rounding each number to 1 significant figure. 87.4 × 0.3727\n\nWhat number should replace 87.4 in her estimation?\n\n[90] [87] [88] [80]",
        4: "Julie wants to estimate the answer to this calculation by rounding each number to 1 significant figure. 87.4 × 0.3727\n\nWhat number should replace 0.3727 in her estimation?\n\n[0.4] [0.3] [0] [0.3000]",
        5: "What is this number rounded to the nearest whole number? 43.5036\n\n[44] [40] [43.5] [43]",
    },
    "e901": {  # Order fractions 3
        1: "Tom and Katie are discussing fractions:\nTom says 1/7 is greater than 1/5\nKatie says 2/7 is greater than 2/5\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        2: "Tom and Katie are discussing fractions:\nTom says 3/8 is greater than 3/5\nKatie says 7/8 is greater than 7/10\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        3: "Which signs belong in the boxes to make the statement correct?\n4/5 [?] 3/4\n\n[<] [>] [=] [cannot tell]",
        4: "Which signs belong in the boxes to make the statement correct?\n3/5 [?] 9/15\n\n[<] [>] [=] [cannot tell]",
        5: "Which signs belong in the boxes to make the statement correct?\n7/12 [?] 2/3\n\n[<] [>] [=] [cannot tell]",
    },
    "e92o": {  # Best buy problems
        1: "Per 100ml, which drink is the best value for money? You can use your calculator to help you.\n\n[1 litre for £1.60] [500 ml for 75p] [330ml for 55p] [200 ml for 35p]",
        2: "A small 400g jar of sauce costs 60p. A big 600g jar of sauce costs 85p. Tom needs 1200g of sauce.\n\nWhich jar should he buy, and how much does he save compared to picking the other jar?\n\n[Three small jars save 5p] [Three small jars save 10p] [Two big jars save 5p] [Two big jars save 10p]",
        3: "Tom and Katie are discussing best value.\nTom says £1 for 300g is better value than 50p for 140g\nKatie says £1 for 300g is better value than £2 for 500g\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        4: "Per £1, which drink is the best value for money? You can use your calculator to help you.\n\n[1 litre for £3] [500 ml for £1.60] [330ml for £1.10] [200 ml for 55p]",
        5: "A small 250g jar of sauce costs £1.50. A big 300g jar of sauce costs £2. Tom has £6 and wants as much sauce as possible.\n\nWhich jar should he buy, and how much extra sauce does he get compared to picking the other jar?\n\n[Four small jars get 200g more] [Four small jars get 100g more] [Three big jars get 100g more] [Three big jars get 50g more]",
    },
    "el8s": {  # Bounds of error 1
        1: "A number, rounded to the nearest 10, is 50.\nWhat is the upper bound of that number?\n\n[55] [60] [54] [50.9]",
        2: "A number, rounded to the nearest 10, is 500.\nWhat is the lower bound of that number?\n\n[495] [490] [450] [499.5]",
        3: "A number, rounded to one decimal place, is 3.4.\nWhat is the lower bound of that number?\n\n[3.35] [3.49] [3] [3.3]",
        4: "A number, rounded to two decimal places, is 0.46.\nWhat is the lower bound of that number?\n\n[0.455] [0.45] [0.40] [0.450]",
        5: "Rounded to Nearest 10: Number = 50, Upper Bound = ?, Lower Bound = ?\nWhat number should go in the shaded box?\n\n[54] [55] [60] [54.9]",
    },
    "embt": {  # Probability of a single event 4
        1: "The table shows the probabilities that a sweet taken at random from a large bag will be yellow, or will be green, or will be blue, or will be red.\n\nYellow | Green | Blue | Red\nProbability | 0.21 | 0.14 | ? | 0.3\n\nWhat is the probability the sweet is blue?\n\n[0.35] [0.65] [0.25] [0.21]",
        2: "The table shows the probabilities that a sweet taken at random from a large bag will be yellow, or will be green, or will be blue, or will be red.\n\nYellow | Green | Blue | Red\nProbability | 0.15 | 0.26 | 0.3 | ?\n\nWhat is the probability the sweet is red?\n\n[0.71] [0.29] [0.39] [0.19]",
        3: "Gerard plays sports each week, he either plays squash, tennis or rugby.\nThe probability that Gerard plays squash is 1/6\nThe probability that Gerard plays tennis is 3/8\n\nCalculate the probability that Gerard plays rugby.\n\n[11/24] [13/24] [1/3] [5/12]",
        4: "The audience of a concert is made up by men, women and children in the ratio of 2:4:7.\n\nWhat is the probability a person picked at random is a woman?\n\n[4/13] [1/3] [4/9] [4/7]",
        5: "The table shows the probabilities that a sweet taken at random from a large bag will be yellow, or will be green, or will be blue, or will be red.\n\nYellow | Green | Blue | Red\nProbability x | 0.4 | x | 0.3\n\nWhich is the first correct statement?\n\n[x = 0.3] [x = 0.15] [x = 0.25] [x = 0.35]",
    },
    "emcv": {  # Solve one step linear equations 2
        1: "Solve the equation: 12 = 3p\n\n[p = 36] [p = 4] [p = 9] [p = 15]",
        2: "Solve the equation: p/3 = 12\n\n[p = 36] [p = 4] [p = 9] [p = 15]",
        3: "Solve the equation: 12 = 3/p\n\n[p = 36] [p = 4] [p = 0.25] [There are no solutions]",
        4: "Solve the equation: 12 = 3p\n\n[p = 36] [p = 4] [p = 9] [p = 15]",
        5: "Solve the equation: p/3 = -12\n\n[p = -36] [p = -4] [p = -9] [p = -15]",
    },
    "emkd": {  # Written addition and subtraction of decimals
        1: "How should you line up the digits to calculate 0.7 + 0.54?\n\n[Option A - decimal points aligned] [Option B - right-aligned] [Option C - left-aligned] [Option D]",
        2: "How should you line up the digits to calculate 3 - 0.105?\n\n[Option A] [Option B] [Option C] [Option D]",
        3: "0.51 - 0.202 =\n\n[0.151] [0.312] [0.308] [0.318]",
        4: "3.215 - 1.4 =\n\n[1.815] [4.615] [4.219] [2.215]",
        5: "0.15 - 0.5 =\n\n[0.35] [-0.45] [-0.35] [0.65]",
    },
    "emkk": {  # Plans and elevations
        1: "Kate has the following view:\nFrom which side is she viewing the shape?\n\n[Front] [Side] [Plan] [Back]",
        2: "The following shape is made from seven cubes. Which of these is a plan view of the shape?\n\n[A] [B] [C] [D]",
        3: "Which of the following is the correct 3D shape to match these views?\nPlan / Side / Front\n\n[A] [B] [C] [D]",
        4: "What are the correct views?\n\n[A - Plan/Front/Side] [B - Front/Side/Plan] [C - Side/Plan/Front] [D - Front/Plan/Side]",
        5: "Helen has the following view:\nFrom which side is she viewing the shape?\n\n[Front] [Side] [Plan] [Back]",
    },
    "emlb": {  # Expand single brackets 3
        1: "What is the answer to 4c × 5d?\n\n[20cd] [45cd] [20c²d²] [9cd]",
        2: "Expand and simplify: 4(2x + 1) - (5x - 9)\n\n[3x - 5] [3x + 13] [13x - 5] [13x + 13]",
        3: "Expand and simplify: 2a - 4(3 - a)\n\n[6a - 12] [-2a - 12] [6a + 12] [-2a + 12]",
        4: "The area of these shapes are equal.\nBlue shape: 4 by (3x - 2), Yellow shape: 2 by (5x + 2)\nWhich of these is correct?\n\n[12x - 8 = 10x + 4] [12x - 2 = 10x + 2] [8 + 6x - 4 = 4 + 10x + 4] [4 + 3x - 2 = 2 + 5x + 2]",
        5: "Rectangle: (4x + 9) by (5x + 1)\nWhich of the following statements is incorrect?\n\n[4x + 9 = 5x + 1 so x = 8] [Area = 5x² + x] [Perimeter = 10x + 18] [x = 8]",
    },
    "emn0": {  # Addition and subtraction with negative numbers 1
        1: "What number belongs in the box?\n\n(-4) + 3 = [ ]\n\n[-1] [1] [-7] [7]",
        2: "Which of the following calculations is represented on the thermometer?\n\n[4 + 5 = -1] [-1 + 5 = 4] [-1 + 4 = 5] [1 + 4 = 5]",
        3: "What number belongs in the box?\n\n(-4) + (-3) = [ ]\n\n[-7] [-1] [1] [7]",
        4: "What number belongs in the box?\n\n(-8) + 3 = [ ]\n\n[-5] [11] [-11] [5]",
        5: "The value of the top brick is equal to the sum of the two bottom bricks.\n\nTop: ?, Bottom: [-2] and [4]\nWhat number should replace the star?\n\n[-6] [-4] [6] [4]",
    },
    "emnt": {  # Estimation 3
        1: "Erin wants to check that she has enough money to pay for 12 tickets at £2.45 each.\nWhich calculation will give an overestimate?\n\n[12 × 2] [10 × 2.45] [12 × 2.5] [12 × 2.45]",
        2: "Estimate 3269 × 138\n\n[300,000] [420,000] [330,000] [451,122]",
        3: "Estimate the value of (4.12 × 18.3) / 0.226\n\n[14.4] [16] [400] [360]",
        4: "Which of the following would be a correct first step for an estimation to (4.36 × 127) / 0.51?\n\n[4 × 130 / 0.5] [4 × 100 / 0.5] [4 × 100 / 0.05] [4 × 100 / 1]",
        5: "Tom and Katie are discussing how to estimate the answer to 38.8745 + 7.9302\nTom says 40 + 7.9302 would give an overestimate.\nKatie says 38.8745 + 8 would give an overestimate.\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
    },
    "emo8": {  # Averages and range from a frequency table 3
        1: "The table shows the numbers of TVs in the households of students in a different class.\n\nTVs: 0 1 2 3 4\nFreq: 0 7 2 5 12\n\nWhat is the range for the number of TVs?\n\n[3] [12] [10] [4]",
        2: "The table shows the numbers of TVs in the households of students in a class.\nTom and Katie are arguing about what would happen if all the frequencies doubled.\nTom says the mean would double.\nKatie says the range would double.\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        3: "What is the mean shoe size?\n\nShoe Size: 2 3 4 5 6\nFrequency: 5 8 9 5 3\n\n[3.77] [5.65] [4.50] [1.50]",
        4: "What is the median number of siblings?\n\nSiblings: 0 1 2 3\nFrequency: 4 3 9 10\n\n[4] [3] [2] [1]",
        5: "The table below is a summary of the number of spots counted on 20 ladybirds. Calculate the mean number of spots per ladybird.\n\nSpots: 5 3 4 12 6\nFreq: ? ? ? ? ?\n\n[0.2 (1dp)] [32.75] [4.5] [6.3]",
    },
    "emrc": {  # Solve linear inequalities 1
        1: "How should you write the solution to the following inequality?\n2x < 9\n\n[x < 4.5] [x > 4.5] [x = 4.5] [x < 4]",
        2: "Which number line represents the solution to 2x + 3 < 5?\n\n[A - open circle at 1, left arrow] [B - closed circle at 1, left] [C - open circle at 1, right] [D - closed circle at 1, right]",
        3: "Tom and Katie are arguing about the solution to this inequality: 15 > 4m\nTom says m could be 4\nKatie says m could be 3.75\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        4: "Tom and Katie are arguing about the solution to this inequality: t + 1 > 0.04\nTom says t could be 0\nKatie says t could be -0.9\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        5: "Solve the inequality: -3 > p - 1\n\n[p < -2] [p > -2] [p < -4] [p > -4]",
    },
    "emt1": {  # Factors and multiples 4
        1: "Tom and Katie are arguing about this ring of 12 equally spaced dots.\nTom says you can connect dots to make a regular hexagon.\nKatie says you can connect dots to make a regular octagon.\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        2: "If you can connect dots to draw a regular octagon in a ring of equally spaced dots, which other regular shape can you definitely draw?\n\n[Equilateral triangle] [Square] [Pentagon] [Hexagon]",
        3: "Lucy has three cards with numbers written on them.\n'I have a square number, a prime number and a multiple of 6.'\nWhich set of numbers could Lucy have?\n\n[4, 9, 24] [8, 3, 60] [9, 1, 12] [9, 5, 54]",
        4: "'Common multiples of 2, 3 and 5 are also multiples of 30'\nIs this statement...\n\n[Always true] [Sometimes true] [Never true] [Impossible to say]",
        5: "Tom and Katie are arguing about multiples.\nTom says that if n is a positive integer, 6 + n will always be a multiple of 6.\nKatie says that if n is a positive integer, 6n will always be a multiple of 6.\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
    },
    "emtg": {  # Fractions and recurring decimals 1
        1: "Which of these two decimals is recurring?\n0.333 and 0.3̇\n\n[0.333] [0.3̇] [Both] [Neither]",
        2: "Which of these fractions converts to a recurring decimal?\n\n[1/2] [1/3] [1/4] [1/5]",
        3: "What is 0.51̇ as a fraction?\n\n[0.5151... = ?] [Choose correct conversion]",
        4: "What is 0.5̇1̇ as a fraction?\n\n[51/99] [51/100] [17/33] [51/90]",
        5: "0.351̇ = ?\n\n[0.3515151... = ?] [0.351351... = ?] [0.351351351... = ?] [0.3513131... = ?]",
    },
    "fqu6": {  # Negative numbers - method selection 1
        1: "Tom and Katie are discussing negative numbers.\nTom says -12 > -9\nKatie says -0.401 > -0.41\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        2: "(-3) + 5 =\n\n[2] [-2] [8] [-8]",
        3: "(-3) + (-5) =\n\n[2] [-2] [8] [-8]",
        4: "(-3) - (-5) =\n\n[2] [-2] [8] [-8]",
        5: "(-3) - 5 =\n\n[2] [-2] [8] [-8]",
    },
    "fqut": {  # Volume of non-prisms 1
        1: "Which of the following is not a measure of volume?\n\n[Metres cubed] [Kilometres] [Millilitres] [Cubic centimetres]",
        2: "Sally has answered a question on the volume of a cone and got an answer of 150.\nBehind the star she has written the units that she used.\nWhich of the following units could be correct?\n\n[cm] [m] [cm²] [150★]",
        3: "What is the volume of a sphere with diameter 4cm?\n\n[32π/3 cm³] [8π cm³] [4π cm³] [16π cm³]",
        4: "Tom and Katie are discussing how to work out the volume of a hemisphere.\nTom says you could use the formula: 2πr³/3\nKatie says you could use the formula: 4πr³/3 divided by 2\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        5: "Jessica is trying to work out the volume of this cone.\nFirst she needs the perpendicular height.\nWhich of the following formulae would help her work out the value of h?\n\n[c² = a² + b²] [A = bh/2] [sin(θ) = O/H] [cos(θ) = A/H]",
    },
    "fqwi": {  # Algebraic proof 2
        1: "'If n is a positive integer, then 4n is an even number'\nIs the above statement always true, sometimes true, or never true?\n\n[Always true] [Sometimes true] [Never true] [I'd just be guessing]",
        2: "Which of the following expressions is always a multiple of 5 if n is a positive integer?\n\n[n + 5] [2n + 3] [10n] [5n + 2]",
        3: "'If n is a positive integer, then 3n + 1 is an odd number'\nIs the above statement always true, sometimes true, or never true?\n\n[Always true] [Sometimes true] [Never true] [I'd just be guessing]",
        4: "Which of these always produces consecutive numbers if n is a positive integer?\n\n[n, n+1, n+2] [n, 2n, 3n] [3n, 2n, n] [n, n+2, n+4]",
        5: "'If n is a positive integer, then (2n - 13)² is negative'\nIs the above statement always true, sometimes true, or never true?\n\n[Always true] [Sometimes true] [Never true] [I'd just be guessing]",
    },
    "fqwj": {  # Algebraic fractions - method selection 3
        1: "Simplify the following, if possible:\n(t² + 1) / (t + 1)\n\n[t] [t² + 1] [t - 1] [Does not simplify]",
        2: "Simplify the following, if possible:\n(t² + 2t + 1) / (t + 1)\n\n[t + 2] [t² + t] [t + 1] [Does not simplify]",
        3: "Simplify the following, if possible:\n(t² + t + 2) / (t + 1)\n\n[t + 2] [t² + 1] [Does not simplify] [t + 1]",
        4: "Simplify the following, if possible:\n(t² + t - 2) / (t - 1)\n\n[t + 2] [t - 1] [t - 2] [Does not simplify]",
        5: "Write the following as a single fraction, giving your answer as simply as possible:\n(t² + t - 2)/5 × 15/(t - 1)\n\n[3(t² + t - 2)/(t - 1)] [3t - 3] [3t + 6] [15(t² + t - 2)/5(t - 1)]",
    },
    "fqxe": {  # Function notation 3
        1: "g(x) = x² - x\nWrite an expression for 3g(x)\n\n[9x² - 3x] [3x² - 3x] [3x² - x] [9x² - x]",
        2: "h(x) = 1 - x³\nCalculate the value of h(½)\n\n[⅞] [⅞] [1⅛] [-⅛]",
        3: "h(x) = 1 - x³\nCalculate the value of h(-5)\n\n[126] [-124] [124] [-126]",
        4: "h(x) = 1 - x³\nWrite down an expression for h(2x)\n\n[1 - 8x³] [1 - 2x³] [2 - 8x³] [2(1 - x³)]",
        5: "h(x) = 1 - x³\nWrite an expression for h(x)/x\n\n[(1 - x³)/x] [1/x - x²] [1 - x²] [x - x⁴]",
    },
    "fqxr": {  # Straight line graphs - method selection 4
        1: "A line has equation 4x + 3y = 5\nWhat is its gradient?\n\n[-4/3] [4/3] [3/4] [-3/4]",
        2: "Which of the following lines is not parallel to y = 5x + 1?\n\n[y = 1 - 5x] [y = 5(4 + ½x)] [2y = 10x - 1] [y = 5x - 7]",
        3: "Which of the following lines is perpendicular to y = 2x + 1?\n\n[y = -½x + 3] [y = ½x - 1] [y = -2x + 1] [y = 2x]",
        4: "In which region would x + y = 1 belong?\n\n[Has a positive gradient, crosses y-axis above 0] [Has negative gradient] [Crosses x-axis at (1,0)] [Passes through origin]",
        5: "In which region would 3x + 4y = 3 belong?\n\n[Is parallel to 3x + 4y = 7] [Crosses the x-axis at (1,0)] [Crosses y-axis at (0,1)] [Passes through the origin]",
    },
    "fqzl": {  # Solve linear simultaneous equations graphically 1
        1: "According to the graph, what are the solutions to the simultaneous equations?\n\n[x = ?, y = ?]",
        2: "According to the graph, what are the solutions to the simultaneous equations?\n\n[x = ?, y = ?]",
        3: "According to the graph, what are the solutions to the simultaneous equations?\n\n[x = ?, y = ?]",
        4: "According to the graph, what are the solutions to the simultaneous equations?\n\n[x = 4.2, y = 6.5] [x = 8.2, y = 6.5] [x = 6.5, y = 8.2] [x = 8.2, y = 4.2]",
        5: "According to the graph, what are the solutions to the simultaneous equations?\n\n[x = ?, y = ?]",
    },
    "fso6": {  # Reverse percentages
        1: "Between 2020 and 2021, the population of a city increased by 20%.\nIn 2021, the population of the city was 420,000.\nWhat was the population of the city in 2020?\n\n[504,000] [350,000] [84,000] [336,000]",
        2: "Between 2020 and 2021, the population of a town increased by 5%.\nIn 2021, the population of the town was 86,100.\nWhat was the population of the town in 2020?\n\n[57,400] [81,795] [90,405] [82,000]",
        3: "Between 2020 and 2021, the population of a country increased by 140%.\nIn 2021, the population of the country was p.\nWhich of the following would correctly calculate the population of the country in 2020?\n\n[p / 1.4] [p × 0.6] [p × 1.4] [p / 2.4]",
        4: "Between 2020 and 2021, the population of a town decreased by 35%.\nIn 2021, the population of the town was 94,900.\nWhat was the population of the town in 2020?\n\n[33,215] [128,115] [146,000] [61,685]",
        5: "Between 2020 and 2021, the population of a country decreased by 50.4%.\nIn 2021, the population of the country was q.\nWhich of the following would correctly calculate the population of the country in 2020?\n\n[q / 0.496] [q + 0.504] [q × 0.496] [q / 0.504]",
    },
    "fsq8": {  # Area under a function (curves)
        1: "The velocity (v) time (t) graph shows the velocity of a ball dropped from a ledge.\nRebecca wants to estimate the distance the ball has travelled between 3 and 7 seconds.\nTo do so, she is going to draw a trapezium on the graph.\n\nWhat should she calculate?",
        2: "The velocity (v) time (t) graph shows the velocity of a ball dropped from a ledge.\nRebecca wants to estimate the distance the ball has travelled between 3 and 7 seconds.\nTo do so, she draws a trapezium on the graph.\n\nWhat calculation gives the best estimate?\n\n[area = (a+b)h/2 with specific values]",
        3: "The velocity (v) time (t) graph shows the velocity of a ball dropped from a ledge.\nRebecca wants to estimate the distance the ball has travelled between 3 and 7 seconds.\nTo do so, she calculates the area of a trapezium.",
        4: "The velocity (v) time (t) graph shows the velocity of a ball dropped from a ledge.\nRebecca wants to estimate the distance the ball has travelled between 3 and 7 seconds.\nTo do so, she calculates the area of strips.",
        5: "The velocity (v) time (t) graph shows the velocity of a ball dropped from a ledge.\nRebecca wants to estimate the distance the ball has travelled between 3 and 7 seconds.\nTo do so, she calculates the area of four strips.\n\nIs this an overestimate or underestimate?",
    },
    "fsqj": {  # Recognise common algebraic factors
        1: "Tom and Katie are discussing factors.\nTom says 3 is a common factor of 6x and 9x\nKatie says x is a common factor of 6x and 9x\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        2: "Tom and Katie are discussing factors.\nTom says 2 is a common factor of 4x and 6y\nKatie says x is a common factor of 4x and 6y\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        3: "Tom and Katie are discussing factors.\nTom says a is a common factor of 3ab and 5ac\nKatie says a is a common factor of 3ab and 5bc\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        4: "Tom and Katie are discussing factors.\nTom says 2 and b are common factors of 4ab and 6bc\nKatie says 2b is a common factor of 4ab and 6bc\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        5: "What is the highest common factor of 12xy and 18y²?\n\n[6y] [6xy] [3y] [6]",
    },
    "gev0": {  # Set up a statistical enquiry
        1: "Which of the following is a hypothesis that can be tested?\n\n[Option A] [Option B] [Option C] [Option D]",
        2: "Tom wants to find out if students in Year 7 spend more time on homework than students in Year 11.\nWhich of these would be the best way to collect data?\n\n[Questionnaire] [Observation] [Experiment] [Internet research]",
        3: "Katie wants to find out the most popular brand of trainers in her school.\nWhich of these would be the best sample?\n\n[All students in her class] [50 students from each year group] [All students in Year 10] [50 of her friends]",
        4: "What is wrong with this survey question?\n'Don't you agree that homework is important?'\n\n[It is a leading question] [It has too many options] [It is too vague] [There is nothing wrong with it]",
        5: "A researcher wants to estimate the average height of 15-year-old boys in the UK.\nWhich sample would give the most reliable results?\n\n[A random sample of 50] [A random sample of 500] [Asking all boys in one school] [Measuring the researcher's friends]",
    },
    "gfk1": {  # Find and interpret the range
        1: "What is the range of these numbers?\n5, 7, 11, 14, 18\n\n[13] [12] [11] [18]",
        2: "What is the range of these numbers?\n-3, 2, 5, 8, 11\n\n[14] [8] [11] [5]",
        3: "The range of five numbers is 8.\nFour of the numbers are: 3, 7, 9, 10\nWhat could the fifth number be?\n\n[2] [11] [1 or 11] [18]",
        4: "Which of these sets of numbers has the largest range?\n\n[2, 5, 8, 11] [12, 15, 18, 21] [0, 1, 2, 3] [-5, 0, 5, 10]",
        5: "Tom says: 'If you add 3 to every number in a data set, the range increases by 3.'\nKatie says: 'If you add 3 to every number in a data set, the range stays the same.'\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
    },
    "gg81": {  # Representation of ratio
        1: "What is the ratio of shaded parts to unshaded parts?\n[Diagram showing 3 shaded, 5 unshaded]\n\n[3:5] [5:3] [3:8] [5:8]",
        2: "What is the ratio of circles to triangles?\n[Diagram with 4 circles, 6 triangles]\n\n[4:6] [6:4] [2:3] [3:2]",
        3: "A necklace has red and blue beads in the ratio 2:7.\nThere are 14 red beads. How many blue beads are there?\n\n[49] [28] [21] [35]",
        4: "Share £60 in the ratio 3:2\n\n[£36 and £24] [£40 and £20] [£30 and £30] [£45 and £15]",
        5: "In a class, the ratio of boys to girls is 3:4.\nThere are 12 boys. How many students are in the class?\n\n[28] [21] [16] [12]",
    },
    "ggzm": {  # Use letters to generalise number operations
        1: "Tom and Katie are writing expressions.\nTom says: 'I think of a number n, then add 5' is written as n + 5\nKatie says: 'I think of a number n, then multiply by 3' is written as 3n\n\nWho is correct?\n\n[Only Tom] [Only Katie] [Both Tom and Katie] [Neither is correct]",
        2: "I think of a number, multiply it by 4, then subtract 7.\nIf the number is n, what is the expression?\n\n[4n - 7] [4(n - 7)] [n × 4 - 7] [7 - 4n]",
        3: "I think of a number, add 3, then multiply by 2.\nIf the number is p, what is the expression?\n\n[2(p + 3)] [2p + 3] [p + 3 × 2] [2p + 6]",
        4: "I think of a number, divide it by 5, then subtract 2.\nIf the number is m, what is the expression?\n\n[m/5 - 2] [m/(5 - 2)] [5 - m/2] [(m - 2)/5]",
        5: "Which expression represents: 'I think of a number, square it, then add double the number'?\nIf the number is x.\n\n[x² + 2x] [2x²] [x² + x²] [(x + 2)²]",
    },
}


def clean_text(txt):
    """Remove common OCR artifacts."""
    if not txt:
        return txt
    # Remove "I= Eedi", "l= Eedi", "Eed" prefixes
    for prefix in [
        "I= Eedi I",
        "I= Eedi iS",
        "I= Eedi S",
        "I= Eedi a",
        "I= Eedi Sl",
        "I= Eedi x",
        "I= Eedi",
        "l= Eedi iS",
        "l= Eedi Sl",
        "l= Eedi S",
        "l= Eedi I",
        "l= Eedi",
        "I= Eedi i",
        "Eedi",
        "Eed",
    ]:
        if txt.startswith(prefix):
            txt = txt[len(prefix) :].strip()
            break
    # Remove "© Eedi 2018" and similar
    import re

    txt = re.sub(r"©\s*Eedi\s*\d{4}", "", txt)
    txt = re.sub(r"2\s*kes2018,", "", txt)
    # Remove leading/trailing pipes and whitespace
    txt = txt.strip("| \n")
    # Remove "|" separators (OCR artifact from newlines)
    txt = txt.replace(" |  | ", "\n").replace(" | ", "\n").replace("| ", "\n")
    # Collapse multiple newlines
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def main():
    data_dir = Path("data/eedi_scraped")

    for json_file in sorted(data_dir.glob("*.json")):
        if json_file.name.startswith("_"):
            continue

        with open(json_file) as f:
            quiz = json.load(f)

        qid = quiz["quiz_id"]
        if qid not in CORRECTIONS:
            continue

        modified = False
        for q in quiz["questions"]:
            qnum = q["question_number"]
            if qnum in CORRECTIONS[qid]:
                new_text = CORRECTIONS[qid][qnum]
                if q.get("question_text") != new_text:
                    q["question_text"] = new_text
                    modified = True
            else:
                # Apply generic cleanup
                old = q.get("question_text", "")
                new = clean_text(old)
                if old != new:
                    q["question_text"] = new
                    modified = True

        if modified:
            with open(json_file, "w") as f:
                json.dump(quiz, f, indent=2, ensure_ascii=False)
            print(f"  Fixed: {qid} ({quiz['quiz_name']})")

    # Rebuild aggregate
    all_data = []
    for f in sorted(data_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        with open(f) as fh:
            all_data.append(json.load(fh))

    with open(data_dir / "_aggregated.json", "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"\nDone! {len(CORRECTIONS)} quizzes corrected, aggregate rebuilt.")


if __name__ == "__main__":
    main()

'''#WAP TO CALCULATE THE FACTORIAL OF A NUMBER
#Take user input 
x
=int(input('Enter a number:'))
#Initializing Fact variable as 1
fact=1

#Checking number if its negative
if(x<0):
    #Negative number is a Invalid Input
    print('Invalid Input!')
#Checking if number is 0
elif(x==0):
    #Factorial for 0! is 1
    print('The factorial of 0 is 1.')
#For positive number 
else:
    #Looping through the numbers from 1 to x
    for i in range(1,x+1):
        fact=fact*i #Multiply the fact with every number from 1 to x(recurrsion)
    #Printing the result
    print('The factorial of',x,'! is',fact)

'''
#WAP THAT PRINTS HISTOGRAM OF FREQUENCIES OF THE CHARACTER OCCURING IN A MESSAGE.
#Take user input
x=str(input('Enter a message:'))

#Loop through every character in the input given by user
for ch in set(x):
    #Print the character followed by no of astriks for its frequecy of occurence
    print(ch, ":", x.count(ch) * '*')
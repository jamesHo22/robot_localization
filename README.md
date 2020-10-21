# robot_localization
# James and Sander’s Particle Filter
## Goal
The goal of this project was to understand the basic particle filter algorithm and implement our own version in ROS using a neato robot. The particle filter would allow us to localize our robot within a known map using only measured lidar and odometry data.
## Approach
We started off by defining the four main steps of the algorithm: initialize a set of particles, move each particle by the motor command, compute the weight of each particle given the true sensor reading and particle positions, then resample the particles based on the normalized weights. We used the following methods to perform each step.
### Initializing Particles 
Grab the arrow from the map frame
Use numpy’s random.norm function to generate a list of x, y coordinates centered around our initial guess arrow. 
Publish particles
### Moving Particle
Get dx and dy from the odom movement
Compute the magnitude of the change in position of the robot in the odom frame
Apply the changes in position and orientation to each particle
### Computing the Weights
Each particle is given a weight based on the likelihood of the robot having that particular pose. In order to assess the likelihood we looked at the lidar data. By centering the lidar data around the particle's position, rotating it to match the particle’s orientation. From there we transformed the superimposed lidar points into the map frame. Then we were able to reference the occupancy grid and get values for each point. We arbitrarily decided to weight each particle based on the average occupancy value for the measured lidar data. We would eventually move two only use half of the lidar points in order to run more efficiently. Finally, in order to normalize the weights we divided each weight by the sum of all the weights, such that the sum of the normalized weights equalled 1.
### Resampling Particles
Resample the same number of particles based on the normalized weights using numpy’s ‘’’random.choice()’’’ function. Each resampling step we resampled all particles based on their normalized weights. 
## Notable Design Decision
We intentionally chose a simple approach when it came to determining the weights. We summed all the distances between each point to the wall to determine each particle’s weight. Instead of looking at all the scan points, we look at every 5th scan point so that the computations complete more quickly. This is a parameter we can tune. 
 
## Challenges
The biggest challenge we faced in this project was ensuring all of our objects were in the correct reference frame. We dealt with three different reference frames, the map frame, odom frame, and the base frame. Our end goal was to have each particle and thus the robot pose be given in the map frame, however in order to do this we had to convert many other variables such as the simulated lidar data and the odom movement into the map frame as well.
 
## Next Steps
Currently our project works alright. Relative to the lidar data our particles seem to be converging to the correct location, but we are running into issues where the particles and lidar data are getting offset and rotated such that they didn’t correspond with the map quite right. We improved it by tuning our update distance and angular thresholds for updating the particles using the odom, but there is still a lot of improvement that can be made. Another improvement we could make is optimizing our code so that it runs more efficiently. There are probably some unnecessary for loops that could be removed.   
## Lessons Learned
This project reinforced yet again how important it is to understand the reference frames you are working with. We began by just diving into the project expecting to figure out all of the transforms as problems arose. This didn’t work very well, and we found ourselves having to step back and really think about what it was our code was doing and how the coordinate frames of each object interacted with each other. This made progress slow, debugging hard, and meant we had to rewrite a number of steps. Going forward we have decided it would be good to first brainstorm the whole algorithm step by step and think about what coordinate frames various nodes will be given in and accordingly what conversions need to be made. Then, working out the transformations by hand to get a deep understanding about what is going on behind the scenes. Taking these first steps would hopefully make the implementation process much easier and more straight forward.   

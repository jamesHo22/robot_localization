# robot_localization
# James and Sander’s Particle Filter
## Goal
The goal of this project was to understand the basic particle filter algorithm and implement our own version in ROS using a neato robot. The particle filter would allow us to localize our robot within a known map using only measured lidar and odometry data.
## Approach
We started off by defining the four main steps of the algorithm: initialize a set of particles, move each particle by the motor command, compute the weight of each particle given the true sensor reading and particle positions, then resample the particles based on the normalized weights. We used the following methods to perform each step.
### Initializing Particles 
The algorithm begins by taking an input pose from the user as an initial estimation for the robot's pose. A cloud of 400 particles are created normalized around the input pose. You can see an example of this below along with the distributions used for the initialization position and orientation. In order to calculate this noise we used NumPy's function `random.normal()`.
<p align="center">
  <img width="1208" height="487" src="robot_localizer/bags/InitializationDistributionsGIF.gif">
  
  The following code block shows how each particle's x, y, and angle are calculated using the user's input guess and the generated noise.
  
    for each particle in cloud
      particle.x = estimate.x + noise.x
      particle.y = estimate.y + noise.y
      particle.a = estimate.a + noise.a
      
      
  
### Moving the Particles
Once the particles have been initialized they are updated based on data received from the robot's odometry. The robot's odometry is not completely accurate, so some noise is added. This also allows for multiple particles of the same pose to diverge, preventing all of the particles to converge to the wrong pose. We decided to use a fairly small amount of noise to minimize drifting. An example of a particle drifting from the actual odometry readings based on our amounts of noise is shown below.

<p align="center">
  <img width="1208" height="487" src="robot_localizer/bags/motionModelDistribution.gif">
  
### Computing the Weights
Each particle is given a weight based on the likelihood of the robot having that particular pose. In order to assess the likelihood we looked at the lidar data. We began by centering the lidar data around the particle's position, rotating it to match the particle’s orientation. From there we transformed the superimposed lidar points into the map frame. Then we were able to reference the occupancy grid and get values for each point. We arbitrarily decided to weight each particle based on the average occupancy value for the measured lidar data. We would eventually move two only use half of the lidar points in order to run more efficiently. Finally, in order to normalize the weights we divided each weight by the sum of all the weights, such that the sum of the normalized weights equalled 1.
<p align="center">
  <img width="1300" height="400" src="robot_localizer/bags/particleWeightsCombined.gif">
 The superimposed lidar scan of a single particle can be seen here in green. 
  
### Resampling Particles
Resample the same number of particles based on the normalized weights using numpy’s ‘’’random.choice()’’’ function. Each resampling step we resampled all particles based on their normalized weights. 
<p align="center">
  <img width="1397" height="573" src="robot_localizer/bags/particleFilterAC109.gif">
  Here is an example of our final implementation using 300 particles. It manages to maintain a pretty accurate pose estimate through out the recording.
  
## Notable Design Decision
We intentionally chose a simple approach when it came to determining the weights. We summed all the distances between each point to the wall to determine each particle’s weight. Instead of looking at all the scan points, we look at every 5th scan point so that the computations complete more quickly. This is a parameter we can tune. 
 
## Challenges
The biggest challenge we faced in this project was ensuring all of our objects were in the correct reference frame. We dealt with three different reference frames, the map frame, odom frame, and the base frame. Our end goal was to have each particle and thus the robot pose be given in the map frame, however in order to do this we had to convert many other variables such as the simulated lidar data and the odom movement into the map frame as well.
 
## Next Steps
Currently our project works alright. Relative to the lidar data our particles seem to be converging to the correct location, but we are running into issues where the particles and lidar data are getting offset and rotated such that they didn’t correspond with the map quite right. We improved it by tuning our update distance and angular thresholds for updating the particles using the odom, but there is still a lot of improvement that can be made. Another improvement we could make is optimizing our code so that it runs more efficiently. There are probably some unnecessary for loops that could be removed.   
## Lessons Learned
This project reinforced yet again how important it is to understand the reference frames you are working with. We began by just diving into the project expecting to figure out all of the transforms as problems arose. This didn’t work very well, and we found ourselves having to step back and really think about what it was our code was doing and how the coordinate frames of each object interacted with each other. This made progress slow, debugging hard, and meant we had to rewrite a number of steps. Going forward we have decided it would be good to first brainstorm the whole algorithm step by step and think about what coordinate frames various nodes will be given in and accordingly what conversions need to be made. Then, working out the transformations by hand to get a deep understanding about what is going on behind the scenes. Taking these first steps would hopefully make the implementation process much easier and more straight forward.   

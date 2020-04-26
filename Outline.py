import torch
import torch.nn as nn
import torch.nn.functional as F


class Net(nn.module):
    def __init__(self):
        super(Net,self).__init__()
        self.spatial = Spatial_Des()
        self.structural = Structural_Des()
        self.Mesh1 = Mesh1()
        self.Mesh2 = Mesh2()
        self.Mesh3 = Mesh3()
        self.mlp1 = mlp1()              # mlp left to implement
        self.mlp2 = mlp2()
        self.mlp3 = mlp3()
        
    
    def forward(self,x):
       # center = x[:,3]
       # corner = x[:,3:12]
       # normal = x[:,12:15]
       # neighbour_index = x[:,15:18]                  #ignore this,will fix this once i get the data format
        
        y = self.spatial(center)
        z = self.structural(corner,normal,neighbour_index)
        out1,out2 = self.Mesh1(y,z,neighbour_index)
        out3,out4 = self.Mesh2(out1,out2,neighbour_index)
        
        out5 = torch.cat((out3,out4),0)
        out5 = self.mlp1(out5)
        
        out6 = torch.cat((out5,out3),0)
        out6 = torch.cat((out6,out1),0)
        
        out6 = self.mlp2(out6)
        
        final_output = self.mlp3(out6)
        
        return final_output
         
        


# In[ ]:


class spatial_Des(nn.module):
    def __init__(self):
        super(spatial_Des,self).__init__()
        self.linear1 = nn.Linear(n*3,n*64)
        self.linear2 = nn.Linear(n*64,n*64)
        
    def forward(self,x):
        x = F.relu(self.linear1(x))
        x = self.linear2(x)
        return x


# In[ ]:


class structural_Des(nn.module):
    def __init__(self):
        super(structural_Des,self).__init__()
        self.kc = Kernel_Correlation(4)
        self.frc = Face_Rotate_Conv()
        self.linear1 = nn.Linear(131,131)
        self.linear2 = nn.Linear(131,131)
        
    def forward(self,corner,normal,neighbour):
        x = self.frc(corner)
        z = self.kc(normal,neighbour)
        z = torch.cat((normal,z),0)
        x = torch.cat((z,x),0)
        
        x = self.linear2(F.relu(self.linear1(x)))
        
        return x
        
        
        


# In[ ]:



class Face_Rotate_Conv(nn.module):
    def __init__(self):
        super(Face_Rotate_Conv,self).__init__()
       # self.linear1 = nn.Linear(9,32)
        #self.linear2 = nn.Linear(32,32)
        self.linear3 = nn.Linear(32,64)
        self.linear4 = nn.Linear(64,64)
        self.conv = nn.Conv1d(1,32,6)

        
    def forward(self,corner):                # corner is n*9 . we take these face wise and apply an mlp on each of them individually
        final_array = torch.zeros(n*64)
        for i in range(n):
            corner_1_i = corner[i*9:i*9+3]
            corner_2_i = corner[i*9+3:i*9+6]
            corner_3_i = corner[i*9+6:i*9+9]

            corner_1_2 = torch.cat((corner_1_i,corner_2_i),0)
            corner_2_3 = torch.cat((corner_2_i,corner_3_i),0)
            corner_3_1 = torch.cat((corner_3_i,corner_1_i),0)

            corner_1_2 = corner_1_2.view(1,1,6)
            corner_2_3 = corner_2_3.view(1,1,6)
            corner_3_1 = corner_3_1.view(1,1,6)

            conv1_2 = self.conv(corner_1_2)
            conv1_2 = conv1_2.view(-1)

            conv2_3 = self.conv(corner_2_3)
            conv2_3 = conv2_3.view(-1)

            conv3_1 = self.conv(corner_3_1)
            conv3_1 = conv3_1.view(-1)


            vec4 = torch.mean(torch.stack([conv1_2,conv2_3,conv3_1]),dim=0)


            vec4 = self.linear4(F.relu(self.linear3(vec4)))
            final_array[i*64:i*64+64] = vec4

        return final_array


class Kernel_Correlation(nn.module):
    def __init__(self):
        super(Kernel_Correlation,self).__init__(self,k,sigma)
        self.learnable_kernel = nn.parameter(torch.ones((64,k,3)),requires_grad = True)


    def forward(self,normal,neighbour):
        final_array = torch.zeros(n*64)
        for i in range(n):
            neighbours = neighbour[3*i:3*i+3] 
            a = neighbours[0]
            b = neighbours[1]         
            c = neighbours[2]                            # a,b,c are the three neighbour indexes
            
            
            normal_i = normal[i*3:i*3+3]
            normal_a = normal[a*3:a*3+3]
            normal_b = normal[b*3:b*3+3]
            normal_c = normal[c*3:c*3+3]

            for m in range(64):
                sum = 0
                for l in range(k):
                    x = normal_i - learnable_kernel[m,l,:]
                    norm = torch.norm(x)
                    sum = sum + exp(-1*norm*norm)/(2*sigma*sigma)

                final_array[i*64,i*64+m] = sum/(k*4)

        return final_array












        
        


# In[ ]:


class Mesh1(nn.module):
    def __init__(self):
        super(Mesh1,self).__init__()
        self.aggregation1 = Aggregation1()
        self.combination1 = Combination1()
        
    def forward(self,spatial,structural,neighbour):
        out1 = self.combination1(spatial,structural)
        out2 = self.aggregation1(structural,neighbour)
        return out1,out2
        
    


# In[ ]:


class Combination1(nn.module):
    def __init__(self):
        super(Combination1,self).__init__()
        self.linear1 = nn.Linear(n*(64+131),n*200)
        self.linear2 = nn.Linear(n*200,n*256)
        
    def forward(self,spatial,structural):
        a1 = torch.cat((spatial,structural),0)    # a1 has size n*(64+131 now)
        a1 = F.relu(self.linear1(a1))            #a1 has size n*200 now
        a1 = self.linear2(a1)
        
        return a1
        
       # a1 = torch.cat((spatial,structural),dim=0)


# In[ ]:


class Aggregation1(nn.module):
    def __init__(self):
        super(Aggregation1,self).__init__()
        self.linear1 = nn.Linear(128,256)
        self.linear2 = nn.Linear(256,128)
        self.linear3 = nn.Linear(n*128,n*512)
        self.linear4 = nn.Linear(n*512,n*256)
        
    def forward(self,structural,neighbour):
        n = len(neighbour)//3                   #neighbour has size n*3 , structural has size n*64
        final_array = torch.zeros(n*128)
        for i in range(n):
            neighbours = neighbour[3*i:3*i+3] 
            a = neighbours[0]
            b = neighbours[1]         
            c = neighbours[2]                            # a,b,c are the three neighbour indexes
            
            
            features_i = structural[i*64:i*64+64]
            features_a = structural[a*64:a*64+64]
            features_b = structural[b*64:b*64+64]
            features_c = structural[c*64:c*64+64]
            
            inp_1 = torch.cat((features_i,features_a),0)
            inp_2 = torch.cat((features_i,features_b),0)
            inp_3 = torch.cat((features_i,features_c),0)
            
            inp_1 = F.relu(self.linear1(inp_1))
            inp_1 = self.linear2(inp_1)
            
            inp_2 = F.relu(self.linear1(inp_2))
            inp_2 = self.linear2(inp_2)
            
            inp_3 = F.relu(self.linear1(inp_3))
            inp_3 = self.linear2(inp_3)
            
            max_1_2 = torch.max(inp_1,inp_2)
            max_1_2_3 = torch.max(max_1_2, inp_3)
            
            final_array[i*128:i*128+128] = max_1_2_3
        
        final_array_1 = F.relu(self.linear3(final_array))
        final_array_2 = self.linear4(final_array_1)
        
        return final_array_2
            
        
        


# In[1]:


'''import numpy as np
a1 = np.array([1,2,3])
a2 = np.array([2,3,4])

a3 = np.append(a1,a2)
print(a3)
'''

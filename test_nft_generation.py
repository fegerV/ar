#!/usr/bin/env python3  
import sys  
sys.path.append('vertex-art-ar')  
from nft_maker import generate_nft_marker  
print('Testing NFT marker generation...')  
result = generate_nft_marker('test_image.jpg', 'test_output', False)  
print(f'Generation result: {result}') 

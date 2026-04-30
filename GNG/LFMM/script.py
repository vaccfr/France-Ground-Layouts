import os

def create_folder_files():
    # Get the directory where this script is located
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Loop through all items in that directory
    for item in os.listdir(script_directory):
        item_path = os.path.join(script_directory, item)

        # Check if the current item is a folder
        if os.path.isdir(item_path):
            folder_name = item

            # Define the 4 file names based on the folder's name
            file_names = [
                f"{folder_name} AVISO.txt",
                f"{folder_name} Groundlayout AVISO.txt",
                f"{folder_name} Gates.txt",
                f"{folder_name} Taxiways.txt"
            ]

            # Create the 4 empty files inside this folder
            for file_name in file_names:
                file_path = os.path.join(item_path, file_name)
                
                # Opening a file in 'w' (write) mode creates it. 
                # Using 'pass' immediately closes it, leaving it empty.
                with open(file_path, 'w') as f:
                    pass
                    
    print("Success! Empty text files have been created in all adjacent folders.")

if __name__ == "__main__":
    create_folder_files()
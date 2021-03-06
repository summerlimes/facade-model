from skimage import io
from skimage.measure import find_contours, approximate_polygon, subdivide_polygon
import svgwrite
import os
import numpy as np
import re
import sys
from collections import deque
import time

class Queue:
    """
    A basic queue.
    """
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def enqueue(self, item):
        self.items.insert(0,item)

    def dequeue(self):
        return self.items.pop()

    def size(self):
        return len(self.items)

def create_out_folder():
    """
    Create an out folder within the current working directory.
    """
    cwd = os.getcwd()
    if not os.path.exists(cwd + "/out"):
        os.mkdir(cwd + "/out")

def create_image_folders_in_out(in_dir, out_dir):
    """
    Assuming that the in_dir contains image directories of images, create the
    same folder in the out_dir.

    @params in_dir the input directory with image directories
    @params out_dir this output directory
    """

    # file list in cwd
    l = os.listdir(in_dir)
    for f in l:
        if os.path.isdir(in_dir + "/" + f) and not os.path.exists(out_dir + "/" + f):
            os.mkdir(out_dir + "/" + f)

def floodfill(nest_list, selection_list, x, y, min_ignore=0, max_ignore=255, max_width_flood=0.25, max_length_flood=0.25):
    """
    Select the set of points such that a 2D array's value is not between
    min_ignore and max_ignore and greater than zero. As min_ignore increases,
    the more set of points that are returned (in other words, "whiter
    pixels" are floodfilled as well).

    The bounds for min_ignore and max_ignore is between 0 and 255.
    If the specified min_ignore and max_ignore are not within
    those bounds, then it's automatically set as max being 255 and min as 0.

    @params nest_list the ndarray that is the edge image input
    @params selection_list the ndarray that is to be the mask for the object
    @params x,y the x,y points of the object
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"
    """
    # Base case
    # If current pixel is 1 "white"
    # return and do nothing
    if not 0 < max_ignore <= 255:
        max_ignore = 255
    if not 0 <= min_ignore < 255:
        min_ignore = 0

    max_win_size = (max_width_flood*nest_list.shape[1]) * (max_length_flood*nest_list.shape[0])

    queue = Queue()
    queue.enqueue((x,y))

    checklist_array = {}

    area_pixels = 0
    while not queue.isEmpty(): # Check adjacent neighbor is valid or the filling color
        a, b = queue.dequeue()
        selection_list[b,a] = 255
        checklist_array[(a,b)] = 1
        area_pixels += 1
        # print((a,b) in checklist_array)
        # Up
        if (a,b-1) not in checklist_array and check_valid(a,b-1,nest_list, min_ignore=0, max_ignore=255):
            #print("1")
            queue.enqueue((a, b-1))
            checklist_array[(a,b-1)] = 1
        # Down
        if (a,b+1) not in checklist_array and check_valid(a,b+1,nest_list, min_ignore=0, max_ignore=255):
            #print("2")
            queue.enqueue((a, b+1))
            checklist_array[(a,b+1)] = 1
        # Right
        if (a+1,b) not in checklist_array and check_valid(a+1,b,nest_list, min_ignore=0, max_ignore=255):
            #print("3")
            queue.enqueue((a+1, b))
            checklist_array[(a+1,b)] = 1
        # Left
        if (a-1,b) not in checklist_array and check_valid(a-1,b,nest_list, min_ignore=0, max_ignore=255):
            #print("4")
            queue.enqueue((a-1, b))
            checklist_array[(a-1,b)] = 1

        if area_pixels > max_win_size:
            selection_list = np.zeros((nest_list.shape[0], nest_list.shape[1]), dtype=int)
            return

        # print(str(a) + "," + str(b))
        # print("The queue size is: " + str(queue.size()))
       # time.sleep(5)
       # print(selection_list)

def check_valid(x, y, nest_list, min_ignore=0, max_ignore=255):
    """
    Check if this is a valid x,y point that is within the range of acceptance
    (below the min_ignore but greater than 0.0).

    @params nest_list the ndarray that is the edge image input
    @params x,y the x,y points of the object
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"
    @return true if the pixel is not outside of the image size and not "white"
    """
    height, width = nest_list.shape
    if (x < width and y < height and x >= 0 and y >= 0) and 0.0 <= nest_list[y][x] <= min_ignore:
        return True
    else:
        return False

def check_image(image_list):
    """
    Check if the image is a .png. If not, remove it from the image_list.

    @params image_list a list of image file names
    """
    for image in image_list[:]:
        if image.split(".")[-1] != "png":
            image_list.remove(image)

def find_images(image_directory):
    """
    Return a list of .png image names in an image_directory.

    @params image_directory the absolute path of an image directory
    @return a list of image file names
    """
    im_list = os.listdir(image_directory)
    check_image(im_list)
    return im_list

def import_points_for_image(text_filename, points_folder):
    """
    Retrieve the points list from the points folder.

    @params text_filename a points text file
    @params points_folder the path to the points folder

    @return a list of points for a given image
    """
    points_list = []
    points_folder_list = os.listdir(points_folder)
    for point_file_name in points_folder_list:

        if text_filename.startswith(point_file_name.split(".txt")[0]):
            print(text_filename)
            print(point_file_name.split(".txt")[0])
            with open(points_folder + "/" + point_file_name, 'r') as f:
                for line in f:
                    points_list.append((line.split(" ")[0], line.split(" ")[1]))
    return points_list

def select_object(image_file, x, y, min_ignore=0, max_ignore=255, max_width_flood=0.25, max_length_flood=0.25):
    """
    Selects one object in the image_file based on its x,y point by the floodfill
    algorithm. Return it as a mask.

    @params image_file the path to an image
    @params x,y the x,y coordinates of an object
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"

    @return an nd array of an object
    """
    im_array = io.imread(image_file)
    mask = np.zeros((im_array.shape[0], im_array.shape[1]), dtype=int)
    floodfill(im_array, mask, x, y, min_ignore, max_ignore, max_width_flood, max_length_flood)
    #print(np.nonzero(mask))
    return mask

def approx_polygon(new_object):
    """
    Uses scikitimage approximate_polygon function to approximate polygons
    from a mask of floodfill output

    @parms new_object output mask from floodfill
    """
    contour = find_contours(new_object, 0)[0]
    approx_polygon_coords = approximate_polygon(contour, tolerance=1)
    return (approx_polygon_coords)

def subd_polygon(new_object):
    """
    Uses scikitimage approximate_polygon function to subdivide polygons
    from a mask of floodfill output

    @parms new_object output mask from floodfill
    """
    contour = find_contours(new_object, 0)[0]
    subd_polygon_coords = subdivide_polygon(contour, degree=1, preserve_ends=True)
    return (subd_polygon_coords)

def coords_to_vector(out_vector_object, coords):
    """
    Takes output coordinates from approximated polygons and creates
    vector polygons in svg format using svgwrite.

    @params out_vector_object vector object name
    @params coords coordinates returned from approxamated polgyons
    """

    polygon_vector_points = []
    for i in coords:
        polygon_vector_points.append((int(i[0]), int(i[1])))

    #print("creating out_vector_object")
    out_vector_object.add(out_vector_object.polygon(points = polygon_vector_points, stroke="rgb(0,0,0)"))
    out_vector_object.save()
    return None

def select_all_objects(image_file, image_name, points_list, min_ignore=0, max_ignore=255, max_width_flood=0.25, max_length_flood=0.25):
    """
    Selects every object in the image_file based on its points_list and sums
    it into one image. Return all object masks as one mask.

    @params image_file the path to an image
    @params points_list the points of an object in the image
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"

    @return the mask that contains all the objects in an image
    """
    im_array = io.imread(image_file)

    mask = np.zeros((im_array.shape[0], im_array.shape[1]), dtype=int)

    # Finding the output folder for vectors
    output_vectors_folder = find_output_vectors_folder()

    folder_list = os.listdir(output_vectors_folder)

    folder_to_save_in = output_vectors_folder
    for folder in folder_list:
        if image_name.startswith(folder):
            folder_to_save_in = output_vectors_folder + "/" + folder

    # Creating paths for saving two types of output vector file
    out_approx_vector_file = folder_to_save_in + "/" + image_name + "_approx.svg"
    out_subd_vector_file = folder_to_save_in + "/" + image_name + "_subd.svg"

    # Creating vector objects with svgwrite
    out_approx_vector_object = svgwrite.Drawing(out_approx_vector_file, profile="full")
    out_subd_vector_object = svgwrite.Drawing(out_subd_vector_file, profile="full")

    # print(mask.shape)
    for points in points_list:
        # Note that the points are (y,x)

        new_object =  select_object(image_file, int(float(points[1])), int(float(points[0])), min_ignore, max_ignore, max_width_flood, max_length_flood)


        approx_polygon_coords = approx_polygon(new_object)
        subd_polygon_coords = subd_polygon(new_object)

        # adding one polygon vector to vector objects: out_approx_vector_object and out_subd_vector_object
        coords_to_vector(out_approx_vector_object, approx_polygon_coords)
        coords_to_vector(out_subd_vector_object, subd_polygon_coords)

        mask = mask + new_object
        # print ("new object")
        # print (new_object)
        # print ("maask here")
        # print(mask)
    #print(np.nonzero(mask))

    # saving out_approx_vector_object and out_subd_vector_object after all polygons are added
    out_approx_vector_object.save()
    out_subd_vector_object.save()

    mask[mask>1] = 255
    #print(mask)
    return mask

def process_all_images(image_list, img_dir, output_dir, points_folder, min_ignore=0, max_ignore=255, max_width_flood=0.25, max_length_flood=0.25):
    """
    Processes all images from the image_list in img_dir. Saves the points in a points folder in the cwd
    and in ../image_points .

    @params image_file the path to an image
    @params img_dir the image directory path
    @params output_dir the output directory path
    @params points_folder the path of the points folder
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"
    """
    dict_of_selection_masks = {}

    for image_file in image_list:
        image_name = image_file.split(".png")[0]
        img_loc = img_dir + "/" + image_file
        img_points_list = import_points_for_image(image_file.split(".png")[0], points_folder)
        img_mask = select_all_objects(img_loc, image_name, img_points_list, min_ignore, max_ignore, max_width_flood, max_length_flood)
        dict_of_selection_masks[image_file] = img_mask



        output_dir_list = os.listdir(output_dir)
        for folder_name in output_dir_list:
            if image_name.startswith(folder_name):
                io.imsave(output_dir + "/" + folder_name + "/" + image_file, img_mask)
                io.imsave(find_output_shapes_folder() + "/" + folder_name + "/" + image_file, img_mask)
    return dict_of_selection_masks

def process_all_images_of_in_folder(input_dir, output_dir, points_folder, min_ignore=0, max_ignore=255, max_width_flood=0.25, max_length_flood=0.25):
    """
    Precondition: input_dir directory only contains folders.
    Processes all images inside the input directory folder.

    @params input_dir the input directory path
    @params output_dir the output directory path
    @params points_folder the path of the points folder
    @params min_ignore the minimum threshold of a "white pixel"
    @params max_ignore the maximum threshold of a "white pixel"
    """
    subdirs = os.listdir(input_dir)
    for folder_name in subdirs:
        img_dir = input_dir + "/" + folder_name
        img_list = find_images(img_dir)
        image_to_ndarray = process_all_images(img_list, img_dir, output_dir, points_folder, min_ignore, max_ignore)

def save_all_images(directory, ndarray_dict):
    """
    Saves images given a directory and a dictionary of image file names to
    ndarray.

    @params directory the directory that will contain the image folders
    @params ndarray_dict the dictionary that contains all image file names
    """
    for ndarray in ndarray_dict.keys():
        io.imsave(directory + "/" + ndarray.split(".png")[0] + "/" + ndarray)

def find_edge_images_folder():
    """
    Return the edge_images folder.
    """
    cwd = os.getcwd()
    os.chdir("../edge_images")
    edge_images_folder = os.getcwd()
    os.chdir(cwd)
    return edge_images_folder

def find_output_shapes_folder():
    """
    Return the output_shapes folder.
    """
    cwd = os.getcwd()
    if not os.path.exists("../output_shapes"):
        os.mkdir("../output_shapes")
    os.chdir("../output_shapes")
    output_shapes_folder = os.getcwd()
    os.chdir(cwd)
    return output_shapes_folder

def find_output_vectors_folder():
    """
    Return the output_vectors folder.
    """
    cwd = os.getcwd()
    if not os.path.exists("../output_vectors"):
        os.mkdir("../output_vectors")
    os.chdir("../output_vectors")
    output_vectors_folder = os.getcwd()
    os.chdir(cwd)
    return output_vectors_folder

def find_image_points_folder():
    """
    Return the image_points folder.
    """
    cwd = os.getcwd()
    os.chdir("../image_points")
    image_points_folder = os.getcwd()
    os.chdir(cwd)
    return image_points_folder

def main(min_ignore=0.0, max_ignore=255.0, max_width_flood=0.25, max_length_flood=0.25):
    """
    Run the main script.
    """

    os.chdir(os.getcwd() + "/floodfill")

    input_folder = find_edge_images_folder()
    points_folder = find_image_points_folder()
    output_folder = os.getcwd() + "/out"
    output_shapes_folder = find_output_shapes_folder()

    create_out_folder()
    create_image_folders_in_out(input_folder, output_folder)
    create_image_folders_in_out(input_folder, output_shapes_folder)
    create_image_folders_in_out(input_folder, find_output_vectors_folder())

    # list of directories where images are stored
    process_all_images_of_in_folder(input_folder, output_folder, points_folder,
        min_ignore, max_ignore, max_width_flood, max_length_flood)

    os.chdir("..")

if __name__ == "__main__":
    main()

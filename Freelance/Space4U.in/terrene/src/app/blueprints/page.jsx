import Nav from "@/components/Nav/Nav";
import Gallery from "@/components/Gallery/Gallery";

const page = () => {
  return (
    <>
      <Nav />
      <div className="page blueprints">
        <Gallery />
      </div>
    </>
  );
};

export default page;

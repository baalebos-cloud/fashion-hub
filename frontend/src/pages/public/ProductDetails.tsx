import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { productsApi } from "@/api/products.api";
import { ProductDetails as ProductDetailsComponent } from "@/components/marketplace/ProductDetails";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { authRoutes } from "@/config/routes.config";
import { useNavigate } from "react-router-dom";
import type { VendorProduct } from "@/types/product";

export default function ProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<VendorProduct | null>(null);

  useEffect(() => {
    if (productId) productsApi.getById(productId).then(setProduct);
  }, [productId]);

  if (!product) return <LoadingScreen label="Loading product…" />;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <ProductDetailsComponent
        product={product}
        variants={[]}
        inventory={null}
        onAddToCart={async () => {
          // Public visitors aren't authenticated as a professional yet —
          // send them to sign in/up before they can actually add to cart.
          navigate(authRoutes.login);
        }}
      />
    </div>
  );
}
